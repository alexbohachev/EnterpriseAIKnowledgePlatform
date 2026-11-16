# EAKP Stage 3 — результати перевірки

Дата: 2026-11-16. Версія кодової бази: v0.3.

- **8/8 pytest-тестів пройшли** (локальна SQLite).
- `alembic upgrade head`: перевірено на тимчасовій SQLite DB; у тесті міграції перевірено наявність 9 проєктних таблиць.
- `python -m compileall -q app alembic tests`: перевірено.
- YAML-файл Compose успішно розібрано; перевірено internal network / відсутність публічних портів БД / залежність worker від healthcheck API.
- Python-wheel пакета `enterprise_ai_knowledge_platform-0.3.0-py3-none-any.whl` зібрано через pip без скачування залежностей.
- Позитивні тести: login, документи, grants user/group, worker для PDF із текстом і збереженням page_number.
- Негативні тести: forged JWT, owner spoofing, 401/404, групові revoke, 12MB upload limit, неприпустимий PDF header, scanned PDF → NEEDS_OCR, `/query` → 501.
- **Немає підтвердження:** Docker Engine/real PostgreSQL integration, справжнє egress blocking, GPU, LLM, GraphRAG, OCR, p95/RPS, production hardening.

Повторна перевірка:

```bash
cd enterprise_ai_knowledge_platform_stage3
PYTHONPATH=. pytest -q
```
