# Stage 8 — короткий опис для портфоліо / LinkedIn / OTUS

## Українською (2–3 речення)

**Enterprise AI Knowledge Platform (EAKP)** — корпоративна RAG-платформа з ACL, GraphRAG-lite, локальним LLM (Ollama) і OCR сканів. На синтетичному Docker-стенді підтверджено повний E2E: ingest → індексація (Qdrant/Neo4j) → запити з цитуванням, ізоляція користувачів, OCR smoke, RAG eval (8+4 кейси, faithfulness). Автоматичний gate: `mvp_acceptance: PASS` (`160ebd7`). Код і live-архів: [репозиторій](https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform) · [ZIP-докази](https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform/releases/tag/stage8-submission-2026-11-17).

**Не заявляю:** production-ready, air-gap, GPU bench, semantic KG, multimodal VLM, pen-test (`release_acceptance: BLOCKED` — див. OPEN register).

## English (portfolio)

Synthetic Docker live evidence for an on-prem **Enterprise AI Knowledge Platform**: ACL-aware RAG, GraphRAG-lite, local LLM, OCR for scanned PDFs. Reproducible `demo_from_zero` scripts; bundled reports with `mvp_acceptance: PASS` (commit `160ebd7`). Not production-certified; formal GPU/air-gap/semantic-graph scope documented as OPEN.

## Посилання в одному рядку

```
Repo: https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform
Release: https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform/releases/tag/stage8-submission-2026-11-17
Evidence ZIP: EAKP_Stage8_Live_Evidence_2026-11-19.zip (mvp PASS, 160ebd7)
```