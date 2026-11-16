# Backend directory mapping

The tested Python package is maintained at `../app/`; migration files live at `../alembic/` and tests at `../tests/`. This avoids breakage of `uvicorn app.main:app`, `python -m app.worker`, and Docker build context. A future repo restructure may move these directories only after all commands/imports/Compose paths have been updated and E2E checks rerun.
