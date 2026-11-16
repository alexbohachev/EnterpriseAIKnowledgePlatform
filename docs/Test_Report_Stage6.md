# EAKP Stage 6 — verification & measurement report

**Evidence type:** code/unit/API/static tests + a small local uvicorn HTTP diagnostic.

| Verification | Actual outcome | Meaning |
|---|---|---|
| `python -m pytest -q` | **37 passed** | SQLite + fake adapters; deterministic local tests |
| Uvicorn `/healthz` | **200** | Local process alive |
| Uvicorn `/readyz` | **200** | SQLite `SELECT 1`; real PostgreSQL NOT tested |
| `/internal/metrics` without valid token | **403** | Protected when metrics enabled |
| `/internal/metrics` with valid token | **200** | Client obtained Prometheus-format response |
| `/healthz` HTTP probe | **12/12 successes; ~4.19 RPS; p95 15.56ms** | Very small local client diagnostic; NOT LLM query benchmark |
| Docker Compose entire stack | **NOT EXECUTED** | Docker Engine unavailable in authoring environment |
| Collector/Jaeger/Grafana real end-to-end | **NOT EXECUTED** | Config prepared, no live traces/screenshots |
| Qdrant/Neo4j/Ollama and local model inference | **NOT EXECUTED** | No live integration |
| Real RAG evaluation | **NOT EXECUTED** | Runner exists, dataset must be curated |
| Real query load / GPU utilization | **NOT EXECUTED** | No real RPS/p95 tokens/s claimed |
| Production penetration/PII guarantees | **NOT EXECUTED** | Prior guardrails only best effort |

The diagnostic `/healthz` test had 12 observations (2.862s), which is far too small for a reliable p95 estimate. The measurement is included for provenance, **not** as a service SLO or architectural performance proof.

## Acceptance gates remaining

- G1 live dependency test (PostgreSQL, Qdrant, Neo4j, Ollama): **OPEN**.
- G2 real synthetic document upload → index → query → ACL deny/grant/revoke: **OPEN**.
- G3 Prometheus+Grafana+Jaeger tested with live, nonsensitive requests: **OPEN**.
- G4 annotated evaluation of real answers plus independent human factuality review: **OPEN**.
- G5 query load report (measured RPS, p50/p95, errors, hardware/model): **OPEN**.
- G6 threat/risk/security review and actual air-gap network enforcement: **OPEN**.

**Conclusion:** Stage 6 code, tests and launchable monitoring templates have been created; **operational acceptance is not closed** without a real deployed stack.
