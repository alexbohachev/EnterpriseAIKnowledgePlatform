# Stage 7 — інструкція оператора та приймальний прогін

## 0. Передумови
Тільки ізольована **тестова** мережа, синтетичні PDF і два тестові облікові записи A/B. Потрібні Docker Engine, Docker Compose v2, попередньо перевірені образи, дисковий простір під локальні Ollama моделі (`bge-m3`, `qwen2.5:3b` за конфігурацією), відповідні secrets. Справжню ізоляцію air-gap забезпечувати засобами хоста/маршрутизатора: Docker `internal: true` сам по собі не є актом перевірки.

## 1. Підготовка
```bash
cp .env.example .env
# Заповніть EAKP_DB_PASSWORD, EAKP_NEO4J_PASSWORD, EAKP_JWT_SECRET; не комітьте .env
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose exec api python -m app.integration_probe
```
Після оновлення конфігурації перевірте, що API/worker/indexer в очікуваних мережах; доступ до Redis/баз із public ingress заборонений; HTTP 127.0.0.1:8000 — лише для локальної лабораторії. Якщо proxy на remote: HTTPS і security review обов'язкові.

## 2. Створіть тестових користувачів
```bash
docker compose exec api python -m app.cli create-user --email alice@test.local
docker compose exec api python -m app.cli create-user --email bob@test.local
```
Скрипт інтеграційного smoke очікує синтетичних A і B. Задайте їхні паролі тільки у змінних середовища, без вставлення у звіт і git.

## 3. Перевірка реального E2E (OPEN ДО ВИКОНАННЯ)
```bash
export EAKP_TEST_ALICE_EMAIL=alice@test.local EAKP_TEST_ALICE_PASSWORD='SET_LOCALLY'
export EAKP_TEST_BOB_EMAIL=bob@test.local EAKP_TEST_BOB_PASSWORD='SET_LOCALLY'
python scripts/integration_smoke.py --accept-synthetic-write --output reports/integration_smoke.json
```
Потрібні статус INDEXED, наявність citations для A, відсутність документів у B, grant/revoke. `NEEDS_OCR` для скану — відома функціональна прогалина, не успіх.

## 4. Спостережуваність (OPEN ДО ВИКОНАННЯ)
Згенеруйте незалежний токен метрик і пароль Grafana, синхронізуйте `.env` і `.secrets/metrics_token`, включіть OTLP endpoint, запустіть профіль: 
```bash
docker compose --profile monitoring up -d --build
```
Зберігайте лише синтетичні screenshots: Grafana overview, Jaeger end-to-end trace, Neo4j graph visualization, `docker compose ps`; не показуйте secrets, prompts, корпоративні дані.

## 5. Quality evaluation (OPEN)
Заведіть вручну анотований набір без реальних секретів. Замініть шаблонні IDs у `examples/eval_template.jsonl`. Запустіть `scripts/evaluate_rag.py --dataset <safe.jsonl> --output reports/rag_eval.json`. Звіт має містити набір, модель, версію, recall/citation metrics, а також ручну factuality-перевірку і failure cases. Не називайте метрику citation validity доказом правдивості.

## 6. Нагрузочний тест (OPEN)
```bash
python scripts/load_test.py --mode query --seconds 30 --rps 0.4 --concurrency 2 \
  --accept-real-load --output reports/load_results.json
```
Повторити на warm модельному середовищі; підняти concurrency поступово; записати CPU/GPU, RAM/VRAM, model, quantization, context size, TTFT/p50/p95/p99, tokens/s, success RPS/error ratio. Успішний healthz probe ≠ inference throughput.

## 7. Акцепт і безпека
Закрити R04 (складні графові відношення) та R05 (OCR/таблиці/зображення) або формально погодити обмеження викладачем. Перевірити реальну мережеву ізоляцію, секрети, доступ до сховищ, PII/adversarial dataset і ролі. Лише після цього маркувати реліз як ACCEPTED.
