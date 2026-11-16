# Stage 8 — приймальні перевірки і OCR для EAKP

**Цей пакет розширює Stage 7. Він НЕ є підтверджено прийнятим Production-продуктом.**

Додано локальний OCR сканованих PDF; HTTP/SQLite/GraphRAG перевіряється зі штучними адаптерами, а **live Docker E2E/OCR/RAG/load** задокументовані в `docs/Stage8_Submission_Checklist_UA.md` і релізі [`stage8-live-evidence-2026-11-16`](https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform/releases/tag/stage8-live-evidence-2026-11-16). Air-gap, семантичний граф, multimodal і GPU-benchmark лишаються OPEN.

Основний план і обмеження: `docs/Stage8_Acceptance_Gap_Analysis_UA.md`.  
Зібрати локальні докази: `python scripts/stage8_preflight.py`.  
На справжньому Docker-стенді: `python scripts/ocr_live_smoke.py --accept-synthetic-write`.

# Enterprise AI Knowledge Platform — OTUS Architect AI/ML

**Stage 7 · Defense / submission candidate (Ukrainian docs, Python sources)**

## IMPORTANT — acceptance status
The 7-stage **documentation and code packaging** cycle is complete, but this is **NOT a verified, ready-for-production product or a fully accepted OTUS submission**. CI runs `pytest` on SQLite/fake adapters (see `.github/workflows/ci.yml`). A **synthetic Docker live evidence bundle** exists (release tag above); it does not replace production acceptance. Verified air-gap enforcement, pen testing, semantic knowledge graph quality, diagram/table understanding, and GPU/token benchmarks remain **OPEN / NOT MEASURED** unless your operator environment reproduces and extends the bundled reports.

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
Run `python -m pytest -q` locally or rely on GitHub Actions CI. Passing unit tests do not prove multi-service integration without your Docker runbook artifacts under `reports/`.

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
