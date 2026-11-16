"""One-shot *real* dependency probe. Run inside the API container after Docker starts.

Does not send user data to any service, does not create collections, and does not
claim platform readiness merely because /readyz checks PostgreSQL.
"""
from __future__ import annotations
import json
import sys
import time
import httpx
from sqlalchemy import text
from .config import Settings
from .db import make_session_factory


def check_dependencies(cfg: Settings) -> dict:
    results = {}

    def probe(name, fn):
        started = time.perf_counter()
        try:
            detail = fn()
            results[name] = {"ok": True, "latency_ms": round(1000 * (time.perf_counter() - started), 1), "detail": detail}
        except Exception as exc:
            results[name] = {"ok": False, "latency_ms": round(1000 * (time.perf_counter() - started), 1), "error_type": type(exc).__name__}

    def postgres():
        engine, factory = make_session_factory(cfg.database_url)
        try:
            with factory() as db:
                db.execute(text("SELECT 1"))
        finally:
            engine.dispose()
        return "SQL query succeeds"

    def qdrant():
        with httpx.Client(timeout=5, trust_env=False) as c:
            response = c.get(cfg.qdrant_url.rstrip('/') + '/healthz')
            response.raise_for_status()
        return "HTTP /healthz succeeds; collection presence not tested"

    def neo4j():
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password))
        try:
            driver.verify_connectivity()
        finally:
            driver.close()
        return "Bolt connectivity succeeds"

    def _ollama_model_present(requested: str, installed: set[str]) -> bool:
        if requested in installed:
            return True
        base = requested.partition(":")[0]
        return any(name.partition(":")[0] == base for name in installed)

    def ollama():
        with httpx.Client(timeout=7, trust_env=False) as c:
            response = c.get(cfg.ollama_url.rstrip('/') + '/api/tags')
            response.raise_for_status()
            models = {m.get('name') for m in response.json().get('models', [])}
        absent = [
            model
            for model in (cfg.chat_model, cfg.embedding_model)
            if not _ollama_model_present(model, models)
        ]
        if absent:
            raise RuntimeError('Some configured Ollama models are missing')
        return "Both configured Ollama model names are present (not inference-tested)"

    for name, fn in (("postgres", postgres), ("qdrant", qdrant), ("neo4j", neo4j), ("ollama", ollama)):
        probe(name, fn)
    return {"overall_ok": all(r['ok'] for r in results.values()), "checks": results}


if __name__ == '__main__':
    outcome = check_dependencies(Settings())
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    sys.exit(0 if outcome['overall_ok'] else 2)
