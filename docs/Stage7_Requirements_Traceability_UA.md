# Stage 7 — матриця відповідності вимогам OTUS

**Офіційне джерело:** наданий `project .txt`. **Статус:** на 16 листопада 2026. Позначка «Документація є» не означає, що система перевірена на реальних сервісах.

| ID | Вимога | Статус | Доказ | Залишок |
|---|---|---|---|---|
| R01 | Закритий контур; без зовнішніх LLM API | Частково | Compose internal backend; Ollama local + host allowlist | Реальний egress/air-gap та DNS audit відсутні |
| R02 | C4 Level 1–3, Deployment, Sequence, ER, DFD | Документація є | diagrams/stage1, diagrams/stage2 | Звірити поточну реалізацію з діаграмами після live E2E |
| R03 | ADR і обґрунтування вибору стека | Документація є | design_baseline/**/adr і docs/ADR-0009..0014 | Актуалізувати рішення після порівняльного вимірювання |
| R04 | GraphRAG: граф знань, векторний пошук | Частково | app/rag/*, Neo4j/Qdrant, ADR-0011 | Lexical Entity; typed relation extraction відсутнє |
| R05 | Мультимодальні скани, креслення, складні PDF | Не реалізовано повністю | app/worker.py: PdfReader.extract_text | Немає OCR, table/image/drawing pipeline; NEEDS_OCR |
| R06 | Локальна LLM, quantization, KV-cache plan | Частково | Ollama Qwen2.5:3b і bge-m3 у compose | Немає GPU sizing/доказу квантованої конфігурації/KV cache benchmark |
| R07 | Stateful LangGraph або аналог | Код є | app/rag/workflow.py | Реальний LangGraph на розгорнутому стеку не перевірено |
| R08 | RBAC / ACL; ізоляція A і B | Частково перевірено | SQL ACL + fake API тести; scripts/integration_smoke.py | Live test A/B/revocation на реальних БД — OPEN |
| R09 | Guardrails та PII redaction | Частково | app/guardrails.py; tests/test_security_stage5.py | Евристичні правила, немає adversarial/pen test |
| R10 | Observability: traces, metrics, dashboard | Код і конфігурація | app/observability.py; monitoring/ | Collector/Jaeger/Grafana не запускалися на повному стеку |
| R11 | Демо 5–7 хв і захист 5 хв | Матеріали готові | presentation/; docs/Stage7_Defense_Speech_UA.md | Не записано реального відео, немає live скриншотів |
| R12 | Звіт RPS, p95 і обладнання | Не виміряно | scripts/load_test.py; reports/MEASUREMENTS_REQUIRED.md | healthz 12 запитів ≠ GraphRAG throughput |
| R13 | Repo monorepo: infra/backend/docs | Частково | root app, compose, docs + mapping directories | Для формального layout слід узгодити структуру з інструктором |
| R14 | Підтверджені цитати у відповідях | Частково | app/rag/query.py, source IDs, ACL recheck | Перевірка ID citation ≠ factual consistency/faithfulness |

## Уточнення

Статус R04 — «частково» навіть за наявності Neo4j: поточний граф будується евристиками, не містить підтверджених типізованих семантичних відношень. R05 — істотна невідповідність текстовому опису мультимодальних даних. R12 — відсутня оцінка високопродуктивного інференсу. Без live доказів не заявляти, що формальні критерії приймання виконано.
