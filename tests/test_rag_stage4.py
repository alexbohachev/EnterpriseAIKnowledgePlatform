"""Unit tests with explicitly fake search/embedding/LLM adapters.

They validate authorization and publication logic, NOT actual model quality or
connection to Qdrant, Neo4j, Ollama, Docker or LangGraph.
"""
from app.models import (Document, Chunk, DocumentVersion, IngestionJob, User)
from app.worker import claim_job, process_job
from app.rag.indexing import index_job
from app.rag.query import QueryEngine, AuthorizationChanged
from app.rag.backends import extract_entities
from .conftest import upload
import pytest


class FakeEmbed:
    def embed(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


class FakeVectors:
    dim = 3
    def __init__(self):
        self.records = {}
        self.deleted = []
    def ensure(self):
        return True
    def upsert(self, records):
        for r in records:
            self.records[r['id']] = r
    def delete_run(self, run_id):
        self.deleted.append(run_id)
        self.records = {cid: r for cid, r in self.records.items()
                        if r['payload']['run_id'] != run_id}
    def search(self, vector, document_ids, run_ids, limit=8):
        return [r['id'] for r in self.records.values()
                if r['payload']['document_id'] in document_ids and
                r['payload']['run_id'] in run_ids][:limit]


class FakeGraph:
    def __init__(self, fail=False):
        self.fail = fail
        self.entries = {}
        self.deletes = []
        self.neighbors = []
    def upsert_run(self, run_id, doc_id, chunks):
        if self.fail:
            raise RuntimeError('Simulated graph outage')
        self.entries[run_id] = (doc_id, chunks)
    def expand(self, chunk_ids, limit=24):
        return self.neighbors[:limit]
    def delete_run(self, run_id):
        self.deletes.append(run_id)
        self.entries.pop(run_id, None)


class FakeChat:
    def __init__(self, after=None):
        self.calls = []
        self.after = after
    def answer(self, question, excerpts):
        self.calls.append((question, excerpts))
        if self.after:
            self.after()
        return 'The report confirms a release plan [S1].'


def _indexed(context, tokens, person='alice', vectors=None, graph=None):
    response = upload(context['client'], tokens[person])
    assert response.status_code == 202
    data = response.json()
    with context['sessions']() as db:
        job_id = claim_job(db)
        assert job_id == data['job_id']
        assert process_job(db, context['store'], context['settings'], job_id)
        vectors = vectors or FakeVectors()
        graph = graph or FakeGraph()
        done = index_job(db, context['store'], data['job_id'], FakeEmbed(), vectors, graph)
    return data, vectors, graph, done


def test_stage4_index_published_only_after_both_backends(context, tokens):
    data, vectors, graph, ok = _indexed(context, tokens)
    assert ok
    with context['sessions']() as db:
        job = db.get(IngestionJob, data['job_id'])
        doc = db.get(Document, data['document_id'])
        assert job.status == 'INDEXED'
        assert doc.active_index_run_id == job.index_run_id
        assert all(r['payload']['run_id'] == job.index_run_id for r in vectors.records.values())
        assert len(graph.entries) == 1


def test_stage4_failed_graph_publish_rolls_back_db_and_vectors(context, tokens):
    data, vectors, graph, ok = _indexed(context, tokens, graph=FakeGraph(fail=True))
    assert not ok
    with context['sessions']() as db:
        assert db.get(IngestionJob, data['job_id']).status == 'INDEX_FAILED'
        assert db.get(Document, data['document_id']).active_index_run_id is None
        assert db.query(Chunk).filter_by(version_id=data['version_id']).first().index_run_id is None
        assert not vectors.records
        assert graph.deletes


def test_graphrag_denies_unauthorized_user_even_if_graph_links_secret(context, tokens):
    data, vectors, graph, ok = _indexed(context, tokens)
    assert ok
    with context['sessions']() as db:
        bob = db.get(User, context['users']['bob'])
        chat = FakeChat()
        service = QueryEngine(FakeEmbed(), vectors, graph, chat, context['store'])
        response = service.ask(db, bob, 'What is in the secret report?')
        assert not response.citations
        assert not chat.calls
        alice = db.get(User, context['users']['alice'])
        response = service.ask(db, alice, 'What does the report say?')
        assert len(response.citations) == 1
        assert response.citations[0]['document_id'] == data['document_id']
        assert len(chat.calls) == 1


def test_graph_neighbors_filtered_against_authoritative_sql_acl(context, tokens):
    a, vector, graph, ok = _indexed(context, tokens)
    b, _, _, ok2 = _indexed(context, tokens, person='bob', vectors=vector, graph=graph)
    assert ok and ok2
    bob_chunk = next(cid for cid, r in vector.records.items()
                     if r['payload']['document_id'] == b['document_id'])
    graph.neighbors = [bob_chunk]
    with context['sessions']() as db:
        user = db.get(User, context['users']['alice'])
        chat = FakeChat()
        response = QueryEngine(FakeEmbed(), vector, graph, chat, context['store']).ask(db, user, 'report')
        assert response.citations
        assert all(c['document_id'] == a['document_id'] for c in response.citations)
        assert all(e['document_id'] == a['document_id'] for e in chat.calls[0][1])


def test_mid_generation_acl_revoke_discards_answer(context, tokens):
    c = context['client']
    data, vector, graph, ok = _indexed(context, tokens)
    acl = {'action': 'grant', 'principal_type': 'user',
           'principal_id': context['users']['bob'], 'permission': 'read'}
    assert c.post(f'/api/v1/documents/{data["document_id"]}/acl',
                  headers=tokens['alice'], json=acl).status_code == 200
    def revoke():
        payload = {**acl, 'action': 'revoke'}
        assert c.post(f'/api/v1/documents/{data["document_id"]}/acl',
                      headers=tokens['alice'], json=payload).status_code == 200
    with context['sessions']() as db:
        user = db.get(User, context['users']['bob'])
        service = QueryEngine(FakeEmbed(), vector, graph, FakeChat(after=revoke), context['store'])
        with pytest.raises(AuthorizationChanged):
            service.ask(db, user, 'What does the report say?')


def test_lexical_graph_entity_heuristic_is_real_but_limited():
    assert 'NLP' in extract_entities('NLP and the National Bank published an update.')
    assert 'National Bank' in extract_entities('NLP and the National Bank published an update.')


def test_merge_retrieval_ids_reserves_graph_slots_when_vectors_fill_limit():
    seeds = [f'v{i}' for i in range(6)]
    graph_hits = ['g-only', 'v0']
    merged = QueryEngine._merge_retrieval_ids(seeds, graph_hits, limit=6)
    assert 'g-only' in merged
    assert len(merged) == 6
    assert merged[0] == 'v0'


class SaturatingVectors(FakeVectors):
    def search(self, vector, document_ids, run_ids, limit=8):
        cid = next(iter(self.records))
        return [cid] * limit


def test_retrieve_includes_graph_neighbor_when_vector_hits_saturate_limit(context, tokens):
    data, vector, graph, ok = _indexed(context, tokens, vectors=SaturatingVectors())
    other, _, _, ok2 = _indexed(context, tokens, person='alice', vectors=vector, graph=graph)
    assert ok and ok2
    neighbor = next(
        cid for cid, r in vector.records.items() if r['payload']['document_id'] == other['document_id']
    )
    graph.neighbors = [neighbor]
    with context['sessions']() as db:
        user = db.get(User, context['users']['alice'])
        engine = QueryEngine(FakeEmbed(), vector, graph, FakeChat(), context['store'])
        items = engine.retrieve(db, user, 'report', limit=6)
        chunk_ids = [i['chunk_id'] for i in items]
        assert neighbor in chunk_ids


def test_index_job_resumes_when_status_already_indexing(context, tokens):
    data, vectors, graph, _ = _indexed(context, tokens, vectors=FakeVectors(), graph=FakeGraph())
    vectors.records.clear()
    graph.entries.clear()
    with context['sessions']() as db:
        job = db.get(IngestionJob, data['job_id'])
        job.status = 'TEXT_EXTRACTED'
        job.index_run_id = None
        job.lease_until = None
        doc = db.get(Document, data['document_id'])
        doc.active_index_run_id = None
        db.query(Chunk).filter_by(version_id=data['version_id']).update({'index_run_id': None})
        db.commit()
    with context['sessions']() as db:
        job = db.get(IngestionJob, data['job_id'])
        job.status = 'INDEXING'
        from app.models import utc_now
        from datetime import timedelta
        job.lease_until = utc_now() + timedelta(minutes=30)
        db.commit()
        assert index_job(db, context['store'], data['job_id'], FakeEmbed(), vectors, graph)
        assert db.get(IngestionJob, data['job_id']).status == 'INDEXED'
