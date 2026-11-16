"""Permission-first GraphRAG query. Only SQL is an ACL authority.

External vector/graph indexes hold non-authoritative IDs. SQL active_index_run_id plus
real-time permissions gate every excerpt before the LLM sees it, AND after generation.
"""
from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import (User, Document, DocumentVersion, Chunk, IngestionJob, AuditEvent)
from ..security import allowed
from ..storage import LocalStorage
from ..guardrails import guard_question, sanitize_excerpts, validate_answer


@dataclass
class QueryResult:
    answer: str
    citations: list[dict]
    retrieval_count: int


class AuthorizationChanged(RuntimeError):
    pass


class QueryEngine:
    def __init__(self, embeddings, vectors, graph, chat, store: LocalStorage):
        self.embeddings = embeddings
        self.vectors = vectors
        self.graph = graph
        self.chat = chat
        self.store = store

    def _eligible_documents(self, db: Session, user: User, cap: int = 10_000) -> dict[str, str]:
        # ACL before recency cap: do not drop older accessible docs because newer ones exist globally.
        docs = db.scalars(select(Document).where(Document.active_index_run_id.isnot(None))
                           .order_by(Document.created_at.desc())).all()
        eligible = {d.id: d.active_index_run_id for d in docs if allowed(db, user, d, 'read')}
        if len(eligible) <= cap:
            return eligible
        ordered = [d.id for d in docs if d.id in eligible]
        return {doc_id: eligible[doc_id] for doc_id in ordered[:cap]}

    @staticmethod
    def _merge_retrieval_ids(seed_ids: list[str], graph_ids: list[str], limit: int) -> list[str]:
        """Interleave vector and graph hits so graph expansion is not truncated away."""
        seeds = list(dict.fromkeys(seed_ids))
        graph_only = [cid for cid in dict.fromkeys(graph_ids) if cid not in seeds]
        graph_slots = min(len(graph_only), max(1, limit // 2)) if graph_only else 0
        vector_slots = limit - graph_slots
        merged: list[str] = []
        seen: set[str] = set()

        def add(cid: str) -> None:
            if cid not in seen:
                seen.add(cid)
                merged.append(cid)

        for cid in seeds[:vector_slots]:
            add(cid)
        for cid in graph_only:
            if len(merged) >= limit:
                break
            add(cid)
        for cid in seeds[vector_slots:]:
            if len(merged) >= limit:
                break
            add(cid)
        return merged[:limit]

    def _excerpts(self, db: Session, user: User, chunk_ids: list[str],
                  published: dict[str, str]) -> list[dict]:
        items = []
        for cid in dict.fromkeys(chunk_ids):
            chunk = db.get(Chunk, cid)
            if not chunk:
                continue
            version = db.get(DocumentVersion, chunk.version_id)
            if not version or version.document_id not in published:
                continue
            doc = db.get(Document, version.document_id)
            # Both run AND ACL must be fresh; never trust external payload.
            if (not doc or doc.active_index_run_id != chunk.index_run_id or
                doc.active_index_run_id != published[doc.id] or
                not allowed(db, user, doc, 'read')):
                continue
            text = self.store.path(chunk.text_object_key).read_text(encoding='utf-8')
            items.append({'document_id': doc.id, 'chunk_id': cid,
                          'page_number': chunk.page_number, 'text': text,
                          'acl_epoch': doc.acl_epoch, 'run_id': doc.active_index_run_id})
        return items

    def retrieve(self, db: Session, user: User, question: str, limit: int = 6) -> list[dict]:
        """First LangGraph stage: ACL-filtered retrieval of authoritative SQL chunks."""
        question = guard_question(question)
        published = self._eligible_documents(db, user)
        if not published:
            return []
        embedded = self.embeddings.embed([question])
        if not embedded:
            raise ValueError('Embedding service returned no query vector')
        seed_ids = self.vectors.search(embedded[0], list(published), list(published.values()), limit=limit)
        expanded_ids = self.graph.expand(seed_ids, limit=limit * 3) if seed_ids else []
        merged_ids = self._merge_retrieval_ids(seed_ids, expanded_ids, limit)
        return self._excerpts(db, user, merged_ids, published)[:limit]

    def generate(self, db: Session, user: User, question: str, items: list[dict]) -> QueryResult:
        """Second LangGraph stage: grounded generation then last-moment ACL revalidation."""
        if not items:
            return QueryResult('У доступних документах немає підтвердженої відповіді.', [], 0)
        safe_question = guard_question(question)
        safe_items = sanitize_excerpts(items)
        if not safe_items:
            return QueryResult('Немає безпечного контексту для відповіді.', [], 0)
        token_version = user.token_version
        answer = self.chat.answer(safe_question, safe_items)
        answer = validate_answer(answer, len(safe_items))
        # Reload both membership and ACL from current SQL snapshots after slow model call.
        db.expire_all()
        fresh_user = db.get(User, user.id)
        if not fresh_user or not fresh_user.is_active or fresh_user.token_version != token_version:
            raise AuthorizationChanged('User disabled or token revoked while processing query')
        for item in items:
            doc = db.get(Document, item['document_id'])
            if (not doc or doc.acl_epoch != item['acl_epoch'] or
                doc.active_index_run_id != item['run_id'] or
                not allowed(db, fresh_user, doc, 'read')):
                raise AuthorizationChanged('Access or index changed during query')
        citations = [{'source': f'S{i}', 'document_id': e['document_id'],
                      'chunk_id': e['chunk_id'], 'page_number': e['page_number']}
                     for i, e in enumerate(items, 1)]
        return QueryResult(answer, citations, len(items))

    def ask(self, db: Session, user: User, question: str, limit: int = 6) -> QueryResult:
        return self.generate(db, user, question, self.retrieve(db, user, question, limit))
