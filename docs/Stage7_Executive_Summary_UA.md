# Підсумковий архітектурний висновок

**Назва:** Enterprise AI Knowledge Platform (EAKP).

**Мета OTUS:** захищена автономна платформа корпоративних знань із графовим і векторним retrieval, обмеженням доступу за ACL, локальним LLM та аргументованими архітектурними рішеннями.

**Реалізовано в коді:** FastAPI, міграції PostgreSQL, JWT + ACL, PDF text extraction worker, Qdrant + Neo4j indexer, GraphRAG-lite retrieval, LangGraph workflow, Ollama адаптер, rate limiting, евристичні guardrails, PII regex, базові metrics/traces.

**Перевірено:** 37/37 deterministic tests на SQLite/fakes в Python runtime. Окрема health-only мережна проба з 12 запитів — лише діагностика доступності.

**Не доведено:** реальна Docker інтеграція, on-prem air-gap, мультимодальність сканів/креслень, повноцінний knowledge graph, quality of generation, query RPS/p95, GPU/квантування, security/penetration/compliance.

**Рішення про реліз:** `NO-GO` до закриття G1–G6; для OTUS — показувати як інженерний MVP із прозорими обмеженнями, не як прийнятий виробничий продукт.
