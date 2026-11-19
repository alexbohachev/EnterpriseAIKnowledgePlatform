# Stage 8 — приймальні перевірки і OCR для EAKP

[![CI](https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform/actions/workflows/ci.yml)

**Цей пакет розширює Stage 7. Він НЕ є підтверджено прийнятим Production-продуктом.**

Додано локальний OCR сканованих PDF; CI на `master` — pytest (SQLite/fakes). **Live-докази** генеруються локально в `reports/` (не в git) і пакуються в ZIP після `demo_from_zero` + `publish_stage8_evidence.ps1`. Викладка OTUS: реліз [`stage8-submission-2026-11-17`](https://github.com/alexbohachev/EnterpriseAIKnowledgePlatform/releases/tag/stage8-submission-2026-11-17) — актуальний bundle **`EAKP_Stage8_Live_Evidence_2026-11-17.zip`**, `git_commit` **`7fb553d`** (`mvp_acceptance: PASS` у manifest/preflight). Перезбірка після змін коду: `docs/Stage8_Evidence_Rebuild_UA.md`.

Основний план і обмеження: `docs/Stage8_Acceptance_Gap_Analysis_UA.md`.  
Зібрати локальні докази: `python scripts/stage8_preflight.py`.  
На справжньому Docker-стенді: `python scripts/ocr_live_smoke.py --accept-synthetic-write`.

## Відтворюване демо з нуля (синтетика, throwaway)

Повний прогін: Docker → probe → користувачі Alice/Bob → smoke → OCR → **seed eval (8+4 кейсів)** → RAG eval з **faithfulness** → load → preflight → реєстр OPEN.

```powershell
# Windows (API на 127.0.0.1:8000)
powershell -ExecutionPolicy Bypass -File scripts\demo_from_zero.ps1
```

```bash
# Linux / macOS
chmod +x scripts/demo_from_zero.sh
./scripts/demo_from_zero.sh
```

Паролі: `scripts/demo_env.example`. Eval: `examples/EVAL_DATASETS_UA.md`.  
Після демо: `py -3 scripts/publish_stage8_evidence.ps1` (verify → bundle → GitHub Release).

**OPEN** (semantic graph, multimodal, air-gap, GPU, pentest, відео): `docs/Stage8_Open_Requirements_UA.md`.  
Машиночитний реєстр **не в git** — `reports/open_requirements_register.json` (створює `demo_from_zero` або `scripts/open_requirements_register.py`). Зразок: `examples/stage8_open_requirements_register.example.json`.

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
Or run the single orchestrator: `scripts/demo_from_zero.ps1` / `scripts/demo_from_zero.sh`.  
Manual steps remain in `docs/Stage7_Operator_Runbook_UA.md`. Never use sensitive production documents.

## Why the status is candid
The written OTUS task in `project .txt` demands an air-gapped corporate multimodal GraphRAG solution, deployment/data-flow diagrams, ACL evidence, 5–7-minute demo, and measured RPS/latency. This bundle includes the source and documentation but **not proof of all runtime acceptance criteria**. All unmeasured results are explicitly tagged **OPEN / NOT MEASURED**.
