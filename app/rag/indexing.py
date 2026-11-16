"""Two-index staged publication: only SQL's active run pointer makes an index searchable.

Not a distributed ACID transaction. On partial failure, orphan records are unsearchable by
application SQL gating; best-effort cleanup follows and periodic reconciliation is still needed.
"""
from __future__ import annotations
import time
from uuid import uuid4
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import (IngestionJob, Chunk, DocumentVersion, Document, AuditEvent, utc_now)
from ..storage import LocalStorage
from ..db import make_session_factory
from ..config import Settings
from .backends import OllamaLocal, QdrantLocal, Neo4jLocal


def index_job(session: Session, store: LocalStorage, job_id: str, embedder, vectors, graph) -> bool:
    """Indexes a text-extracted job; failures are reported and never marked READY."""
    job = session.get(IngestionJob, job_id)
    if not job or job.status not in ('TEXT_EXTRACTED', 'INDEXING'):
        return False
    version = session.get(DocumentVersion, job.version_id)
    document = session.get(Document, version.document_id)
    chunks = session.scalars(select(Chunk).where(Chunk.version_id == version.id)
                             .order_by(Chunk.ordinal)).all()
    if not chunks:
        job.status = 'INDEX_FAILED'
        job.failure_code = 'NO_EXTRACTED_CHUNKS'
        session.commit()
        return False
    run_id = str(uuid4())
    # Public graph/vector payload never contains raw corporate document text.
    entries = [{'chunk_id': c.id, 'text': store.path(c.text_object_key).read_text(encoding='utf-8'),
                'page_number': c.page_number, 'document_id': document.id} for c in chunks]
    try:
        vectors.ensure()
        for i in range(0, len(entries), 16):
            batch = entries[i:i+16]
            embeddings = embedder.embed([e['text'] for e in batch])
            if len(embeddings) != len(batch):
                raise ValueError('Embedding batch count mismatch')
            for ent, embedding in zip(batch, embeddings):
                if len(embedding) != vectors.dim:
                    raise ValueError('Embedding dimension mismatch')
            records = [{'id': entry['chunk_id'], 'vector': embedding,
                        'payload': {'chunk_id': entry['chunk_id'], 'document_id': document.id,
                                    'version_id': version.id, 'run_id': run_id}}
                       for entry, embedding in zip(batch, embeddings)]
            vectors.upsert(records)
        graph.upsert_run(run_id, document.id, entries)
        # Publish only AFTER both external writes succeeded. Retrieval crosschecks every chunk.
        document.active_index_run_id = run_id
        for chunk in chunks:
            chunk.index_run_id = run_id
        job.index_run_id = run_id
        job.status = 'INDEXED'
        job.lease_until = None
        job.failure_code = None
        session.add(AuditEvent(actor_id=None, action='index_published',
                               decision='allow', target_id=document.id))
        session.commit()
        return True
    except Exception:
        session.rollback()
        # No partial external index becomes visible; SQL pointer remains unchanged.
        for backend in (vectors, graph):
            try:
                backend.delete_run(run_id)
            except Exception:
                pass
        fail = session.get(IngestionJob, job_id)
        fail.status = 'INDEX_FAILED'
        fail.lease_until = None
        fail.failure_code = 'INDEX_BACKEND_ERROR'
        session.commit()
        return False


def run_forever(poll_seconds=3.0):
    cfg = Settings()
    _, factory = make_session_factory(cfg.database_url)
    store = LocalStorage(cfg.storage_root)
    model = OllamaLocal(cfg.ollama_url, cfg.embedding_model, cfg.chat_model)
    vector = QdrantLocal(cfg.qdrant_url, cfg.qdrant_collection, cfg.embedding_dim)
    graph = Neo4jLocal(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
    print('Stage 4 indexer ready: waiting for TEXT_EXTRACTED documents', flush=True)
    try:
        while True:
            with factory() as session:
                job = session.scalar(select(IngestionJob)
                    .where(IngestionJob.status == 'TEXT_EXTRACTED')
                    .order_by(IngestionJob.created_at).with_for_update(skip_locked=True).limit(1))
                if job:
                    # Claim is not durable until commit; never run multiple indexers on SQLite.
                    job.status = 'INDEXING'
                    job.lease_until = utc_now() + timedelta(minutes=30)
                    job.attempts += 1
                    session.commit()
                    job_id = job.id
                else:
                    job_id = None
            if job_id:
                # A failure is marked INDEX_FAILED and not retried without operator action.
                with factory() as session:
                    index_job(session, store, job_id, model, vector, graph)
            else:
                time.sleep(poll_seconds)
    finally:
        graph.close()


if __name__ == '__main__':
    run_forever()
