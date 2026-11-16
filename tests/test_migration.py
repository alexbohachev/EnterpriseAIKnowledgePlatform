"""Actual Alembic upgrade smoke test, not only Base.metadata.create_all."""
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_initial_migration_produces_runtime_tables(monkeypatch, tmp_path):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("EAKP_DATABASE_URL", url)
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    assert {"users", "groups", "group_memberships", "documents", "document_versions",
            "access_grants", "ingestion_jobs", "chunks", "audit_events"} <= tables
    assert "token_version" in {c["name"] for c in inspect(engine).get_columns("users")}
    engine.dispose()
