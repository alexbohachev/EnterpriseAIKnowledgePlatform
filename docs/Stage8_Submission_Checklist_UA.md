# Stage 8 — чекліст подачі OTUS (оновлено після live-стенда)

## Архів коду та документації
- [x] Monorepo: `app/`, Compose, тести, ADR, діаграми, презентація
- [x] `compose.dev.yaml` для локальної лабораторії (не air-gap демо)
- [x] ZIP-доказів: `reports/EAKP_Stage8_Live_Evidence_*.zip` (`scripts/bundle_stage8_evidence.ps1`)
- [x] Сценарій захисту: `docs/Stage8_OTUS_Defense_UA.md` + `docs/Stage8_OTUS_Demo_Script_UA.md`

## Якість коду та CI (після фіксів GraphRAG / indexer / eval)
- [x] GitHub Actions: `.github/workflows/ci.yml` — `pytest` на push/PR
- [x] Graph retrieve: злиття вектор+граф (`_merge_retrieval_ids`), ACL до cap документів
- [x] Indexer: відновлення прострочених `INDEXING` (lease 30 хв)
- [ ] Локально перепрогнати `python -m pytest -q` перед push (у CI — обов’язково)

## Quality gates для live-звітів (`reports/`)
Після змін у `scripts/evaluate_rag.py` і `scripts/stage8_preflight.py` артефакти мають проходити **автоматичні пороги**, інакше preflight лишає `release_acceptance: BLOCKED`.

| Артефакт | Умова «PASS» |
|---|---|
| `rag_eval.json` | `eval_schema_version >= 2`, усі поля `quality_failures`, `quality_pass_rate`, `faithfulness_pass_rate`; `failed == 0` |
| `rag_eval_bob_acl.json` | те саме (ізоляція Bob / abstain) |
| `load_query.json` | `report_schema_version >= 1`, `provenance == live_http_client_side`, `http_success_ratio >= 0.99`, `p95 <= 60000` |

Перевірка: `python scripts/stage8_preflight.py` → поля `live_rag_eval`, `live_rag_bob_acl`, `live_load_query_report` = `PASS`.

**Розширений набір (faithfulness):** `scripts/seed_synthetic_eval_corpus.py` → `reports/eval_active_alice.jsonl` (8 кейсів) і `eval_active_bob.jsonl` (4 кейси). Поля: `must_not_include`, `require_citation_marks`, `min_citations`. Див. `examples/EVAL_DATASETS_UA.md`.

Автоматичний прогін: `scripts/demo_from_zero.ps1` / `demo_from_zero.sh` (читає `scripts/demo_env.example`).

Окремо RAG eval:
```bash
set EAKP_EVAL_TOKEN=...   # Alice
python scripts/evaluate_rag.py --dataset reports/eval_active_alice.jsonl --output reports/rag_eval.json
set EAKP_EVAL_TOKEN=...   # Bob
python scripts/evaluate_rag.py --dataset reports/eval_active_bob.jsonl --output reports/rag_eval_bob_acl.json
```
У звіті також `faithfulness_pass_rate`. Exit code **2** при провалі quality/faithfulness або `--min-quality-pass-rate`.

## Live Docker — підтверджено на стенді (синтетичні дані)
- [x] Postgres + Qdrant + Neo4j + Ollama + api/worker/indexer
- [x] `integration_probe` → `overall_ok: true`
- [x] `integration_smoke.json` — upload, INDEXED, ACL grant/revoke, RAG citation
- [x] `ocr_live_e2e.json` — сканований PDF → INDEXED → citation
- [x] `rag_eval.json` (Alice) + `rag_eval_bob_acl.json` (ізоляція Bob) — **з quality gates вище**
- [x] `load_health.json`, `load_query.json` (клієнтські HTTP, не GPU) — **load_query з порогом p95/ratio**
- [x] Monitoring: Grafana dashboard, Prometheus scrape, Jaeger UI
- [x] Скріни: `reports/screenshots/` (Grafana, Jaeger; Swagger за потреби — з браузера)

## Досі OPEN (не стверджувати без доказів)
Детально: `docs/Stage8_Open_Requirements_UA.md`; машиночитний реєстр: `python scripts/open_requirements_register.py`.

- [ ] Формальний air-gap audit (egress, образи, DNS)
- [ ] GPU tokens/s, повний inference benchmark
- [ ] Pen-test / adversarial corpus з незалежною перевіркою
- [ ] Semantic knowledge graph (зараз GraphRAG-lite)
- [ ] Multimodal: креслення, складні таблиці (OCR ≠ VLM)
- [ ] Записане 5–7 хв демо-відео з прихованими секретами
- [ ] Підпис викладача / формальний ACCEPTED

## Перед завантаженням у OTUS
1. `python scripts/stage8_preflight.py` — pytest + quality gates звітів
2. Перегенерувати ZIP: `powershell -File scripts\bundle_stage8_evidence.ps1`
3. Додати презентацію: `presentation/EAKP_OTUS_Defense_UA.pptx` (+ PDF)
4. Перевірити, що в архіві **немає** `.env`, `.secrets/`, реальних PDF
5. У захисті проговорити addendum: `docs/Stage8_Defense_Speech_Addendum_UA.md`

**Висновок:** Stage 8 — інженерний MVP з документованими live-доказами на синтетичному стенді; **не** production-ready і **не** повна техприйомка OTUS.