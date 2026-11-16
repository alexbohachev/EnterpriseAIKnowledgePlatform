"""Cross-module acceptance against real SQLite/HTTP, simulated search/LLM adapters.

This is NOT equivalent to a real Docker/Ollama/Neo4j/Qdrant or deployed LangGraph E2E.
"""
from app.models import User
from app.worker import claim_job, process_job
from app.rag.indexing import index_job
from app.rag.query import QueryEngine
from .conftest import upload
from .test_rag_stage4 import FakeEmbed, FakeVectors, FakeGraph, FakeChat


def test_http_upload_worker_index_acl_query_in_one_flow(context, tokens):
    client = context['client']
    doc = upload(client, tokens['alice'])
    assert doc.status_code == 202
    data = doc.json()
    vectors, graph, chat = FakeVectors(), FakeGraph(), FakeChat()
    with context['sessions']() as db:
        job_id = claim_job(db)
        assert job_id == data['job_id']
        assert process_job(db, context['store'], context['settings'], job_id)
        assert index_job(db, context['store'], job_id, FakeEmbed(), vectors, graph)
    assert client.get(f'/api/v1/jobs/{job_id}', headers=tokens['alice']).json()['status'] == 'INDEXED'
    assert client.get(f'/api/v1/documents/{data["document_id"]}', headers=tokens['bob']).status_code == 404
    with context['sessions']() as db:
        alice = db.get(User, context['users']['alice'])
        bob = db.get(User, context['users']['bob'])
        engine = QueryEngine(FakeEmbed(), vectors, graph, chat, context['store'])
        a = engine.ask(db, alice, 'What is the release plan?')
        b = engine.ask(db, bob, 'What is the release plan?')
    assert len(a.citations) == 1 and a.citations[0]['document_id'] == data['document_id']
    assert b.citations == []
    assert len(chat.calls) == 1
    grant = {'action':'grant','principal_type':'user','principal_id':context['users']['bob'], 'permission':'read'}
    assert client.post(f'/api/v1/documents/{data["document_id"]}/acl', headers=tokens['alice'], json=grant).status_code == 200
    assert client.get(f'/api/v1/documents/{data["document_id"]}', headers=tokens['bob']).status_code == 200
    grant['action'] = 'revoke'
    assert client.post(f'/api/v1/documents/{data["document_id"]}/acl', headers=tokens['alice'], json=grant).status_code == 200
    assert client.get(f'/api/v1/documents/{data["document_id"]}', headers=tokens['bob']).status_code == 404
