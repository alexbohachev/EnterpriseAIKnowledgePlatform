# Лист до викладача OTUS (готово до копіювання)

**Тема:** Enterprise AI Knowledge Platform — Stage 8, live-докази на синтетичному стенді

Шановний(а) викладачу,

Надаю пакет захисту за темою **Enterprise AI Knowledge Platform** (локальний LLM, GraphRAG-lite, ACL, OCR сканів).

**Матеріали:**
1. Код: https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform (`master`, коміт у manifest ZIP).  
2. Live-докази (ZIP): https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform/releases/download/stage8-submission-2026-11-17/EAKP_Stage8_Live_Evidence_2026-11-19.zip  
   У `stage8_preflight.json`: **`mvp_acceptance: PASS`**, `git_commit` збігається з кодом на момент збірки (перевірка: `scripts/verify_mvp_evidence.py`).  
3. Презентація: https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform/releases/download/stage8-submission-2026-11-17/EAKP_OTUS_Defense_Stage8_UA.pptx  
4. Сценарій захисту: `docs/Stage8_Defense_5min_UA.md`, чекліст: `docs/Stage8_Submission_Checklist_UA.md`.

**Підтверджено на Docker (синтетичні PDF, Alice/Bob):** integration smoke (ingest, INDEXED, ACL revoke/grant, RAG з цитатами), OCR live E2E на скані, RAG evaluation 8+4 кейсів (faithfulness), клієнтський load-query, integration_probe, observability (Grafana/Prometheus/Jaeger). Відтворення: `scripts/demo_from_zero.ps1`.

**Не заявляю без доказів:** air-gap сертифікацію, GPU tokens/s, повноцінний semantic knowledge graph, multimodal/VLM, penetration test. У звіті: **`release_acceptance: BLOCKED`**. Готовий(а) узгодити зменшений scope відповідно до рубрики курсу.

Дякую за перегляд.

З повагою,  
**Олександр Богачев**  
19 листопада 2026 р.

---

*Якщо ім’я в дипломі інше — замініть підпис; ім’я викладача можна додати в звернення.*