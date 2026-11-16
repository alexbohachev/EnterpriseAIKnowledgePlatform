# Stage 5 — перевірки 16.11.2026

- Команда: `pytest -q -ra`
- Результат: **28 passed** (8 Stage 3 + 6 Stage 4 + 14 Stage 5).
- Синтаксис: `python -m compileall -q app tests` — успішно.
- Міграція `0002_stage5` перевірена при Alembic upgrade до `head` на тимчасовій SQLite.
- Python wheel `0.5.0` зібрано; `app/rag/query.py`, `app/guardrails.py`, `app/ratelimit.py` присутні в артефакті.
- PDF 4 сторінки A4, усі сторінки відрендерені та візуально перевірені, перевірені межі тексту.

**Застереження:** тестове оточення не має Docker Engine, Neo4j, Qdrant, Ollama або встановленого LangGraph. Перевірки Stage 4 використовують FakeChat/FakeVectors/FakeGraph; Stage 5 — TestClient і SQLite. Не запускалися реальні контейнерні сервіси, пентест, E2E, GPU, сканування PDF на malware чи еталонні дані для оцінювання prompt injection / PII.

**Пріоритет Stage 6:** спочатку реальна інтеграція і мережеві негативні тести, далі trace+metrics, load+quality eval.
