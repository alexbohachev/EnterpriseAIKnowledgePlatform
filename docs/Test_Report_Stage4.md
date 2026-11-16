# EAKP Stage 4 — результати перевірок

Перевірки в контейнері створення артефактів (без доступного Docker Engine, без локальних Neo4j/Qdrant/Ollama і без встановленого LangGraph):

- Python syntax: `python -m compileall -q app tests` — успішно.
- `pytest -q --disable-warnings` — **14 passed** (8 Stage 3 + 6 Stage 4).
- Stage 4: publication after both backend writes; compensation on graph failure; SQL ACL-gated query; graph-neighbor ACL filter; revocation during generation; entity heuristic.
- Test doubles: FakeEmbed / FakeVectors / FakeGraph / FakeChat. Це не live tests.
- Неперевірено: LangGraph runtime, HTTP Qdrant, Neo4j Cypher runtime, Ollama inference, Ollama embeddings dimension, Docker Compose, GPU, air-gap, OCR, p95/RPS/retrieval metrics.

Висновок: функціональний прототип у вихідному коді; **production readiness не доведено**.
