# Stage 8 — OCR та перевірка приймання: статуси, які не можна підміняти

## Реалізовано і перевірено локально
- Додано **опційне, повністю локальне OCR** на основі Tesseract + PyMuPDF для сканованих PDF; збережено номери сторінок і обмеження ресурсів.
- Worker розрізняє `TEXT_EXTRACTED`, `NEEDS_OCR`, `FAILED`; OCR-результат **не означає**, що індекс Qdrant+Neo4j уже опубліковано.
- Додано наскрізний тест HTTP/SQLite/worker/indexer/query з контрольованими фальшивими адаптерами пошуку/LLM та перевіркою відмови для іншого користувача.
- Проведено *справжній локальний запуск Tesseract* на синтетичному PDF (у режимі тестів).

## Не реалізовано / не підтверджено
- **Live Docker на синтетичному стенді (Windows, листопад 2026):** `integration_smoke.json`, `ocr_live_e2e.json`, `rag_eval*.json`, `load_query.json` — див. `docs/Stage8_Submission_Checklist_UA.md` і GitHub Release `stage8-live-evidence-2026-11-16`. Це **не** заміна production air-gap, pen test чи GPU/token benchmark.
- OCR — це **видобування тексту**, а не розуміння креслень, складних таблиць чи мультимодальний VLM.
- GraphRAG — lexical entity co-mention, а не повноцінне виявлення семантичних відносин.
- Guardrails й обмеження OCR не є песочницею для довільних PDF; потрібні окремий sandbox, AV сканування і threat modeling.
- Апаратні показники GPU, токенів/с, p95 та factuality ще **не виміряно**. Це відкриті вимоги до захисту.

## Порядок акцепту на комп'ютері з Docker
1. Використати лише синтетичні дані та власну тестову інфраструктуру. Перевірити Docker/Compose, GPU, підготовлені образи та Ollama-моделі.
2. Згенерувати секрети в `.env`; перевірити `docker compose config --quiet`, `docker compose up -d --build`, `docker compose ps`.
3. Виконати `docker compose exec api python -m app.integration_probe`. Звіт — у журнал.
4. Створити користувачів Alice/Bob через `python -m app.cli create-user`; виконати `scripts/integration_smoke.py` та **сканований PDF**, перевірити `INDEXED` і ACL grant/revoke.
5. Виміряти реальні RPS/p50/p95/p99 (лише `/api/v1/query`, не `/healthz`), TPS та VRAM, зберегти модель, квантування, залізо й параметри навантаження.
6. Провести ручну перевірку відповідності відповідей джерелам, adverse prompt injection і tenant isolation.
7. Зібрати артефакти Grafana, Jaeger і Neo4j та відео 5–7 хвилин; приховати секрети й токени.
8. Статус `ACCEPTED` виставити **лише** за наявності всіх доказів і погодженого викладачем scope.

## Запуск локальних тестів

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
```

Тести з реальним Tesseract можуть пропускатися на машинах, де його немає. В Docker-збірці Stage 8 OCR встановлюється через apt, тому для air-gap потрібно підготувати базові образи та пакети завчасно. Це **вхідна залежність збірки**, а не зовнішній API під час інференсу.

## Сканований PDF: реальна операторська перевірка (OPEN)

```bash
# Після Docker Compose і створення тестового користувача:
python scripts/ocr_live_smoke.py --accept-synthetic-write \
    --output reports/ocr_live_e2e.json
```

Доказом слугує лише **справжній успішний** JSON із реального стенда; синтетичний локальний pytest — це інша, нижча категорія впевненості.

## Локальна попередня перевірка

```bash
python scripts/stage8_preflight.py
```

Вихід `reports/stage8_preflight.json` залишає `release_acceptance=BLOCKED`, поки відсутні незалежні технічні докази зі стенда.
