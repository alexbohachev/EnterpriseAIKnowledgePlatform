# Stage 8 — чекліст подачі OTUS (оновлено після live-стенда)

## Архів коду та документації
- [x] Monorepo: `app/`, Compose, тести, ADR, діаграми, презентація
- [x] `compose.dev.yaml` для локальної лабораторії (не air-gap демо)
- [x] ZIP-доказів: `reports/EAKP_Stage8_Live_Evidence_*.zip` (`scripts/bundle_stage8_evidence.ps1`)
- [x] Сценарій захисту: `docs/Stage8_OTUS_Defense_UA.md` + `docs/Stage8_OTUS_Demo_Script_UA.md`

## Live Docker — підтверджено на стенді (синтетичні дані)
- [x] Postgres + Qdrant + Neo4j + Ollama + api/worker/indexer
- [x] `integration_probe` → `overall_ok: true`
- [x] `integration_smoke.json` — upload, INDEXED, ACL grant/revoke, RAG citation
- [x] `ocr_live_e2e.json` — сканований PDF → INDEXED → citation
- [x] `rag_eval.json` (Alice) + `rag_eval_bob_acl.json` (ізоляція Bob)
- [x] `load_health.json`, `load_query.json` (клієнтські HTTP, не GPU)
- [x] Monitoring: Grafana dashboard, Prometheus scrape, Jaeger UI
- [x] Скріни: `reports/screenshots/` (Grafana, Jaeger; Swagger за потреби — з браузера)

## Досі OPEN (не стверджувати без доказів)
- [ ] Формальний air-gap audit (egress, образи, DNS)
- [ ] GPU tokens/s, повний inference benchmark
- [ ] Pen-test / adversarial corpus з незалежною перевіркою
- [ ] Semantic knowledge graph (зараз GraphRAG-lite)
- [ ] Multimodal: креслення, складні таблиці (OCR ≠ VLM)
- [ ] Записане 5–7 хв демо-відео з прихованими секретами
- [ ] Підпис викладача / формальний ACCEPTED

## Перед завантаженням у OTUS
1. Перегенерувати ZIP: `powershell -File scripts\bundle_stage8_evidence.ps1`
2. Додати презентацію: `presentation/EAKP_OTUS_Defense_UA.pptx` (+ PDF)
3. Перевірити, що в архіві **немає** `.env`, `.secrets/`, реальних PDF
4. У захисті проговорити addendum: `docs/Stage8_Defense_Speech_Addendum_UA.md`

**Висновок:** Stage 8 — інженерний MVP з документованими live-доказами на синтетичному стенді; **не** production-ready і **не** повна техприйомка OTUS.