# EAKP — Stage 3 implementation backlog (not started)

Status: PLANNED (not evidence of working code). Stages are a suggested delivery sequence.

| Priority | Work | Acceptance check | Depends on |
|---|---|---|---|
| P0 | Monorepo, locked deps, local Docker Compose networks | Services start without public LLM API and without exposed DB ports | Hardware + offline images |
| P0 | PG schema + migration for users/docs/grants/jobs/chunks | Roundtrip + unique constraints pass | ADR-0006, ADR-0007 |
| P0 | FastAPI JWT verifier and policy gate | 401/403/404 + forged identity tests | PG |
| P0 | Scoped ingestion + local PDF/OCR + immutable versions | Scan PDF indexed with page provenance | Local OCR |
| P0 | Qdrant staging + Neo4j staging, active index-run reader | Crash/retry and stale-version tests | ADR-0007 |
| P0 | Negative ACL tests for vector, graph, revoke race | AT-02, AT-03, AT-04 pass | ADR-0006..0008 |
| P1 | Local serving selection: benchmark VRAM, token latency | Record model/quantization/VRAM and p95 | GPU inventory |
| P1 | LangGraph query state machine | No generate before evidence gate | Retrieval |
| P1 | Citation + abstain behavior | AT-07 and citation correctness | Local LLM |
| P1 | Offline/egress and logging security tests | AT-08 + no sensitive prompts logged | Compose + firewall |
| P1 | OTel + Prometheus/Grafana, evaluation/load test | AT-09 with real measurements | Complete pipeline |
| P2 | UI, deployment script, 5–7 minute deep dive video | Reproducible E2E demo | All P0/P1 |

Explicit non-goals now: HA/DR, automatic K8s orchestration, industrial SSO, complex drawing parsing.
