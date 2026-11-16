# Stage 8 — приймальні перевірки і OCR для EAKP

**Цей пакет розширює Stage 7. Він НЕ є підтверджено прийнятим Production-продуктом.**

Додано локальний OCR сканованих PDF; є фактичні локальні тести OCR, а HTTP/SQLite/GraphRAG ланцюжок перевіряється зі штучними адаптерами. **Повне інтеграційне Docker/LLM E2E залишається відкритим**, Docker Engine недоступний у середовищі підготовки.

Основний план і обмеження: `docs/Stage8_Acceptance_Gap_Analysis_UA.md`.  
Зібрати локальні докази: `python scripts/stage8_preflight.py`.  
На справжньому Docker-стенді: `python scripts/ocr_live_smoke.py --accept-synthetic-write`.

# Enterprise AI Knowledge Platform — OTUS Architect AI/ML

**Stage 7 · Defense / submission candidate (Ukrainian docs, Python sources)**

## IMPORTANT — acceptance status
The 7-stage **documentation and code packaging** cycle is complete, but this is **NOT a verified, ready-for-production product or a fully accepted OTUS submission**. The Python test suite has 37 passing tests in this environment using SQLite/fake adapters. Docker Engine was unavailable; no executed full service/LLM E2E test, Qdrant+Neo4j+Ollama inference benchmark, real p95/RPS, verified air-gap, or pen test evidence is included. Scanned PDFs/OCR and image/drawing understanding are still **not implemented**, and the existing graph is a lexical GraphRAG-lite, not a full extracted semantic knowledge graph. Complete these gaps or agree on a reduced scope with the instructor before claiming all rubric requirements satisfied.

## What is included
- `app/` — production-inspired FastAPI, ACL, PDF text extraction worker, indexer, GraphRAG-lite, LangGraph orchestration, security controls and observability.
- `compose.yaml`, `Dockerfile`, `monitoring/`, `alembic/`, `tests/` — runtime/infrastructure source.
- `diagrams/stage1`, `diagrams/stage2`, `diagrams/` — C4, deployment, sequence, data-flow, ER, and code diagrams (DOT, SVG, PNG; some Mermaid).
- `docs/` — stages 1–6 design/ADR, Stage 7 defense notes, traceability matrix and acceptance runbooks.
- `presentation/EAKP_OTUS_Defense_UA.pptx` — editable five-minute defense slide deck; optional PDF copy.
- `EAKP_Stage7_Final_Report_UA.pdf` — final Ukrainian architectural report.
- `scripts/final_preflight.py` — offline static checks and pytest runner.

The original working Python project lives at repository root (`app/` + `alembic/`), not inside `backend/`, to preserve Python imports and existing Docker build paths. `backend/` and `infra/` explain this layout; no fake second deployment tree is provided.

## Reproduce what can be checked without Docker
```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/final_preflight.py
```
Expected verified unit/API suite in the author's Python runtime: **37 passed**. These tests do not prove multi-service integration.

## Run in an isolated Docker test environment (operator required)
```bash
cp .env.example .env
# Edit ALL secrets; stage trusted Docker images and local Ollama models.
docker compose up -d --build
docker compose exec api python -m app.integration_probe
# Create synthetic test users; see docs/Stage7_Operator_Runbook_UA.md
```

### Local browser access (dev overlay, not air-gap)
```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d --build
# API: http://127.0.0.1:8000/docs — backend network is non-internal; omit compose.dev.yaml for lab air-gap.
```
Then run the synthetic E2E, RAG evaluation, query-load and monitor collection flows described in `docs/Stage7_Operator_Runbook_UA.md`. Never use sensitive production documents for the demonstration.

## Why the status is candid
The written OTUS task in `project .txt` demands an air-gapped corporate multimodal GraphRAG solution, deployment/data-flow diagrams, ACL evidence, 5–7-minute demo, and measured RPS/latency. This bundle includes the source and documentation but **not proof of all runtime acceptance criteria**. All unmeasured results are explicitly tagged **OPEN / NOT MEASURED**.
