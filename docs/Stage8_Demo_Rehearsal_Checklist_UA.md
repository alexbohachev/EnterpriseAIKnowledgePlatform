# Репетиція демо (30–45 хв) перед записом відео

## Перед стартом
- [ ] `docker compose -f compose.yaml -f compose.dev.yaml --profile monitoring up -d`
- [ ] http://127.0.0.1:8000/healthz → `alive`
- [ ] http://127.0.0.1:3000/d/eakp-stage6 — панелі не порожні (згенерувати 2–3 query)
- [ ] Закрити `.env`, токени, персональні вкладки; лише синтетичні дані

## Прогін сценарію (з таймером)
| Хв | Дія | Перевірка |
|----|-----|-----------|
| 0:00 | Проблема + C4 (слайд 1–2) | Без вигаданих метрик |
| 0:45 | `docker compose ps` + probe | `overall_ok: true` |
| 1:30 | Swagger `/docs` або готовий smoke JSON | INDEXED у звіті |
| 2:30 | Слайд Stage 8 live | ZIP/release на GitHub |
| 3:30 | Grafana p95 + Jaeger service `eakp-api` | Скрін готовий |
| 4:30 | Обмеження BLOCKED + addendum | Чесний NO-GO |
| 5:30 | Питання викладача (1 відповідь) | PostgreSQL ACL |

## Після репетиції
- [ ] Оновити ZIP: `powershell -File scripts\bundle_stage8_evidence.ps1`
- [ ] За потреби — новий release або прикріпити ZIP у LMS
- [ ] Teleprompter: `docs/Stage8_Demo_Teleprompter_UA.md`