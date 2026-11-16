# Addendum до захисту (≈1 хв) — що змінилось після Stage 7

Вставити після слайду «що перевірено» або замість застарілого тезису «Docker не підтверджено».

**Факти з live-стенда (лише синтетичні PDF і тестові Alice/Bob):**
- Docker Compose + Ollama `bge-m3` / `qwen2.5:3b`: probe, повний smoke E2E, OCR E2E на скані.
- ACL: Bob без цитат з чужого документа (`rag_eval_bob_acl.json`).
- Observability: Grafana (HTTP RPS, query p95), Prometheus, Jaeger.
- Unit/API: **40 passed** (+3 OCR skip на Windows-хості без Tesseract).

**Чесні обмеження (не прибирати):**
- `release_acceptance` у preflight лишається **BLOCKED**.
- `load_query.json` — клієнтський p95 секундного порядку, без GPU tokens/s.
- GraphRAG-lite; air-gap не сертифіковано.

**Одне речення для викладача:** «Ми доповнили Stage 7 архів reproducible live-доказами; scope production і повної рубрики — окрема домовленість.»