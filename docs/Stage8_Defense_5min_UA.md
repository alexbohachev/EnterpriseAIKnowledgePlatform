# Захист Stage 8 — план на 5 хв (по слайдах)

Презентація: `presentation/EAKP_OTUS_Defense_Stage8_UA.pptx` (9 слайдів).  
Текст для читання з екрана: `docs/Stage8_Demo_Teleprompter_UA.md`.  
Живі команди: `docs/Stage8_OTUS_Demo_Script_UA.md`. Репетиція: `docs/Stage8_Demo_Rehearsal_Checklist_UA.md`.

**Головне повідомлення:** інженерний MVP з **відтворюваними live-доказами** на синтетиці; `mvp_acceptance: PASS`; production і повна рубрика OTUS — **ні** (`release_acceptance: BLOCKED`).

---

## Хронометраж (строго 5:00)

| Час | Слайд | Що сказати (3–4 речення) | Екран / дія |
|-----|-------|---------------------------|-------------|
| **0:00–0:40** | 1–2 | Проблема: PDF і знання без ACL → ризик витоку. Рішення: локальний RAG з цитатами `[S1]` і правами в PostgreSQL. Демо — лише синтетика Alice/Bob. | Слайди; без цифр prod |
| **0:40–1:20** | 3–4 | C4: control plane (API, ACL, LangGraph) vs data plane (Qdrant, Neo4j, Ollama). Індекси не авторитетні для доступу — рішення в SQL до і після LLM. | Вказати стрілки на схемі |
| **1:20–2:00** | 5 | Стек: FastAPI, dual index, Ollama локально. Компроміс: GraphRAG-lite, observability перевіряємо в Docker. | Слайд компромісів |
| **2:00–2:50** | 6 → **9** | **Скіпнути старий «OPEN Docker» на 6:** одразу — «оновлено в Stage 8». pytest **49 passed** (3 skip OCR на хості); live: probe OK, smoke, OCR, RAG eval 8+4, load. **`mvp_acceptance: PASS`** у ZIP. | Показати Release або `stage8_preflight.json` у ZIP |
| **2:50–3:40** | 9 | Три докази: (1) `integration_smoke` — INDEXED + ACL grant/revoke; (2) `ocr_live_e2e` — скан → citation (не VLM); (3) `rag_eval` + Bob ACL + faithfulness. Відтворення: `demo_from_zero.ps1`. | Опційно: `docker compose ps` + probe 10 с |
| **3:40–4:20** | 9 (моніторинг) | Grafana/Jaeger після query; `load_query.json` — **клієнтський** p95, не GPU tokens/s. | Скрін `reports/screenshots/` або localhost |
| **4:20–4:50** | 7 | Чесно: semantic KG, multimodal, air-gap, pentest, GPU — **OPEN**. `release_acceptance: BLOCKED`. | Не вибачатися — це scope |
| **4:50–5:00** | 8 | Roadmap: закрити G1–G6 у продукті; цінність — **керована довіра**, не «LLM на все». Дякую. | Слайд roadmap |

---

## Одне речення на слайд 9 (запам’ятати)

> Ми довели на Docker синтетичний E2E — ingest, подвійний індекс, ACL, OCR скану, RAG eval і observability; архів на GitHub Release збігається з комітом у manifest; до production лишаються air-gap, GPU bench і formal security.

---

## Два режими захисту

### A. Тільки слайди + ZIP (без live Docker на захисті)
- Слайд 9 + вікно з `reports/` з ZIP (або PDF скріни з bundle).
- Плюс: стабільно, без очікування Ollama.
- Мінус: слабший «вау»; компенсувати посиланням на Release і `demo_from_zero`.

### B. Гібрид (рекомендовано, якщо Docker уже піднятий)
- Після слайду 4: `docker compose ps` + `integration_probe` → `overall_ok: true` (≤45 с).
- Потім слайд 9 + Grafana в браузері.
- **Не** гнати повний upload live — достатньо JSON-доказів.

---

## Швидкі відповіді (30 с кожна)

| Питання | Відповідь |
|---------|-----------|
| Це production? | Ні. MVP + synthetic live evidence; `mvp_acceptance: PASS` ≠ production sign-off. |
| Чому BLOCKED? | У preflight перелічені OPEN: air-gap, GPU, semantic graph, pentest — без фальш-доказів. |
| Чому Neo4j і Qdrant? | Два канали recall; ACL застосовується до обох; merge у GraphRAG-lite. |
| OCR = розуміння креслень? | Ні. Tesseract-текст зі скану; VLM/таблиці — OPEN. |
| Як перевірити вдома? | Клон repo → `demo_from_zero.ps1` → `publish_stage8_evidence.ps1` (чесно в README). |

---

## Після захисту (LMS)

1. Скопіювати лист: `docs/Stage8_OTUS_Submission_Cover_Letter_Ready_UA.md` (вставити ім’я викладача за потреби).
2. Додати посилання: repo + Release + PPTX.
3. За бажанням — запис відео за `Stage8_Demo_Rehearsal_Checklist_UA.md` (OPEN у чеклісті, не обов’язково для MVP gate).