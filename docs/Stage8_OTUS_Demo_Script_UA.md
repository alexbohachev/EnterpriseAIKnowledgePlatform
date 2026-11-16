# Сценарій демонстрації OTUS (5–7 хв, синтетичний стенд)

**Статус:** live Docker пройдено на Windows; air-gap/GPU/pen-test — **не заявляти**.

## Перед записом
- `docker compose -f compose.yaml -f compose.dev.yaml --profile monitoring up -d`
- У кадрі: лише синтетичні PDF, `alice@test.local` / `bob@test.local`, без `.env` і токенів
- Підготувати: `reports/stage8_live_evidence_manifest.json`, скріни з `reports/screenshots/`

## 0:00–0:45 — Проблема і архітектура
- Слайд C4 L2: API, PostgreSQL (ACL), worker, Qdrant, Neo4j, Ollama
- Теза: права в SQL, індекси — неавторитетні; revoke через `acl_epoch` / active index run

## 0:45–2:00 — Живий стек (термінал + браузер)
1. `docker compose ps` — api, worker, indexer, db, qdrant, neo4j, ollama healthy
2. `docker compose exec api python -m app.integration_probe` → `overall_ok: true`
3. Браузер: http://127.0.0.1:8000/docs — upload/query endpoints
4. Grafana: http://127.0.0.1:3000/d/eakp-stage6 — HTTP RPS, query p95 (скрін `otus_grafana_dashboard.png`)

## 2:00–3:30 — Ingest + ACL (інтеграційний сценарій)
- Коротко: `reports/integration_smoke.json` — Alice upload → INDEXED → Bob 404 → RAG з цитатою → grant/revoke
- За бажанням live: upload текстового PDF під Alice, показати job `INDEXED`, query з `[S1]` у відповіді

## 3:30–4:30 — OCR (Stage 8)
- `reports/ocr_live_e2e.json` — сканований синтетичний PDF → INDEXED → citation для Project ORION
- Уточнити: OCR — текст зі скану, не креслення/VLM

## 4:30–5:30 — Моніторинг і навантаження (чесні межі)
- Prometheus/Jaeger: UI, сервіс `eakp-api` у Jaeger після query
- `reports/load_query.json`: клієнтський p95 query ~секунди, **не** GPU tokens/s
- `reports/rag_eval.json` + `rag_eval_bob_acl.json`: recall 1.0 і ізоляція Bob

## 5:30–6:30 — Обмеження та NOT ACCEPTED
- GraphRAG-lite (лексичні сутності), не повний semantic KG
- `release_acceptance: BLOCKED` у `stage8_preflight.json` — air-gap, GPU benchmark, pen-test
- Узгоджений reduced scope з викладачем, якщо потрібно

## Закриття (15 с)
Архітектура розділяє довіру (ACL, цитати) і генерацію LLM; live-докази зібрані, production-ready — ні.

## Питання викладача (швидкі відповіді)
| Питання | Відповідь |
|--------|-----------|
| Чому Neo4j + Qdrant? | Два recall-канали; ACL фільтрує обидва |
| Neo4j 5.26 Cypher? | `MERGE … WITH … MATCH` у `app/rag/backends.py` |
| Де air-gap? | `compose.yaml` internal backend; `compose.dev.yaml` — лише для локальної лабораторії |
| p95 query? | Grafana / `load_query.json`; healthz ≠ LLM latency |