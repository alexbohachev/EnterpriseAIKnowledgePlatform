# Checklist перед реальною здачею OTUS

## Матеріали в архіві
- [x] Джерела FastAPI та worker/indexer.
- [x] Тести, Dockerfile та Compose blueprint.
- [x] Діаграми C4 1–4, Deployment, Sequence, DFD, ER.
- [x] ADR 0001–0014, технічні звіти етапів і traceability matrix.
- [x] Презентація 5 хв та промова.
- [x] Шаблони команди запуску й evaluation/bench інструменти.

## Підтвердження для захисту — досі відкриті
- [ ] Live Postgres + Qdrant + Neo4j + Ollama + LangGraph E2E.
- [ ] Збережений proof A/B ACL / revoke на реальних сервісах.
- [ ] Скриншоти реального graph, Jaeger trace, Grafana dashboards і `docker compose ps`.
- [ ] Анотований evaluation set із відповідями моделі, human factuality review.
- [ ] Показники GraphRAG query RPS, p95, TTFT, tokens/s із записом hardware.
- [ ] Air-gap egress check, TLS/proxy, secret handling, незалежний security review.
- [ ] OCR + multimodal extraction для сканів/креслень або погоджене скорочення scope.
- [ ] Typed entity/relation graph або погодження GraphRAG-lite як допустимого MVP.
- [ ] Записане 5–7-хвилинне демонстраційне відео на працездатному стеку.
- [ ] Перевірка викладачем оформлення monorepo / вимог до quantization/serving.

**Висновок:** цей архів є завершеним Stage 7 *пакетом матеріалів*, але ще НЕ готовим для безумовної технічної прийомки.
