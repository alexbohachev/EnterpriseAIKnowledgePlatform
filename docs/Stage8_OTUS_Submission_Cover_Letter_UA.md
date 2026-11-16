# Шаблон звернення до викладача OTUS (лист / коментар до здачі)

**Тема:** Enterprise AI Knowledge Platform — Stage 8, live-докази на синтетичному стенді

Шановний(а) [Ім’я викладача],

Надаю оновлений пакет захисту за варіантом **Enterprise AI Knowledge Platform (GraphRAG + ACL, локальний LLM)**.

**Матеріали:**
1. Вихідний код (публічний репозиторій): https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform  
2. Архів викладки Stage 8: https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform/releases/tag/stage8-submission-2026-11-17  
   **Увага:** ZIP на цьому релізі зібрано до оновлень eval/preflight; після `demo_from_zero` + `bundle_stage8_evidence.ps1` архів і `git_commit` у manifest мають збігатися з поточним `master` (інструкція: `docs/Stage8_Evidence_Rebuild_UA.md`).
3. Презентація: `EAKP_OTUS_Defense_Stage8_UA.pptx` (доданий слайд Stage 8)  
4. Чекліст і сценарій: `docs/Stage8_Submission_Checklist_UA.md`, `docs/Stage8_OTUS_Demo_Script_UA.md`

**Що підтверджено на Docker-стенді (лише синтетичні PDF, користувачі Alice/Bob):**
- повний E2E smoke (ingest → Qdrant+Neo4j → RAG + ACL);
- OCR на сканованому PDF;
- integration_probe, RAG evaluation (у т.ч. faithfulness-поля), клієнтський load-тест;
- відтворення з нуля: `scripts/demo_from_zero.ps1`;
- observability (Grafana, Jaeger).

**Чесно не заявляю:** air-gap сертифікацію, GPU/tokens/s, semantic knowledge graph, multimodal parsing, pen-test. Статус у звіті: `release_acceptance: BLOCKED`. Готовий(а) узгодити зменшений scope, якщо це відповідає рубриці.

Дякую за перегляд.  
[Ваше ім’я]  
[Дата]