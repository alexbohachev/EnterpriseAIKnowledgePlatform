# Stage 6 — операційний runbook (українською)

## Передумови

1. Виділений тестовий сервер або локальна машина з Docker Compose v2.
2. Імпортовані локальні контейнерні образи й моделі Ollama. Вимкнений інтернет або перевірені egress-правила для сценарію air-gap.
3. У `.env` встановлені незалежні секрети PostgreSQL, Neo4j, JWT; у приватному тестовому середовищі налаштовано тестові облікові записи.
4. Для моніторингу створено `.secrets/metrics_token`; той самий токен встановлено в `EAKP_METRICS_TOKEN`, а **інший секрет** — у `EAKP_GRAFANA_ADMIN_PASSWORD`.

## Запуск і health-gates

```bash
docker compose --profile monitoring up --build -d
docker compose ps
docker compose exec api python -m app.integration_probe
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/readyz
```

`/readyz` означає лише доступність SQL. Тест `app.integration_probe` окремо перевіряє PostgreSQL, Qdrant, Neo4j, Ollama і наявність обох моделей; не верифікує генерацію та правильність даних. Наступний gate — `scripts/integration_smoke.py` з **лише синтетичними PDF**.

## Перевірка метрик і трейсів

1. Перевірити, що `/internal/metrics` без токена повертає **403**, а з токеном — **200**.
2. У Prometheus: `up{job="eakp-api"} == 1`; підписані гістограми `eakp_http_request_duration_seconds_*` та `eakp_rag_stage_duration_seconds_*`.
3. У Grafana: дашборд **Enterprise AI Knowledge Platform / Stage 6**.
4. У Jaeger: сервіс `eakp-api` (буде видно після запитів і семплювання 10%).
5. Алерти «HTTP 5xx ratio >5%» та «query p95 >5s» є **попередніми політиками**, не перевіреними на реальному трафіку.

## Gate оцінювання й навантаження

- Позначити синтетичні документи очікуваними `document_id`, відповідями та сценаріями відмови в доступі. Прогнати `scripts/evaluate_rag.py`; не називати recall перевіркою фактологічності.
- Виміряти **запити саме `/api/v1/query`**, зафіксувати GPU, модель, контекст, тип запитань, розігрів, concurrency, помилки 429/503, p50/p95/p99, успішний throughput. Health-check throughput для цього **не підходить**.
- Прогнати багатокористувацькі тести (ізоляція доступу), негативні приклади prompt injection, відкликання ACL під час відповіді. Оцінити ручну перевірку фактів/PII окремо.

## Діагностика

| Симптом | Перевірка | Рішення |
|---|---|---|
| `/readyz`=200, `/query`=503 | `app.integration_probe` і моделі Ollama | Перевірити Qdrant/Neo4j/Ollama та попереднє завантаження моделей |
| Prometheus `up=0` | файл токена, змінна `EAKP_METRICS_TOKEN`, мережа `backend` | Синхронізувати секрети, перевірити `docker compose logs prometheus` |
| Grafana недоступна | `GF_SECURITY_ADMIN_PASSWORD` і `grafana` container logs | Встановити окремий пароль, перезапустити тільки моніторинг |
| Немає span у Jaeger | OTLP endpoint, Collector, sample rate | Перевірити мережу/конфігурацію, згенерувати запити в тестовому середовищі |
| Система повертає 429 | rate limiting per user | Зменшити RPS, використати погоджені тестові акаунти |
| Job зависає | worker/indexer logs та SQL `ingestion_jobs` | Перевірити стани, помилки PDF, модель embeddings, збої зовнішніх індексів |

**Запобіжники:** не передавати секрети через URL, не копіювати відповіді LLM/персональні дані у лог; не показувати моніторинг публічно; мати бекапи; не використовувати результати з Mock/SQLite як свідчення роботи корпоративної інфраструктури.
