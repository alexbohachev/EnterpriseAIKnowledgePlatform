import os
os.environ.setdefault("EAKP_JWT_SECRET", "test-only-secret-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

from io import BytesIO
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from app.config import Settings
from app.db import Base, make_session_factory
from app.main import create_app
from app.models import User
from app.security import hash_password


@pytest.fixture()
def context(tmp_path):
    db_url = f"sqlite:///{tmp_path/'db.sqlite3'}"
    settings = Settings(database_url=db_url, storage_root=tmp_path / "stored")
    engine, sessions = make_session_factory(db_url)
    Base.metadata.create_all(engine)  # migrations separately validated with Alembic
    with sessions() as db:
        admin = User(email="admin@local.test", password_hash=hash_password("StrongPasswordForAdmin!"), role="admin")
        alice = User(email="alice@local.test", password_hash=hash_password("StrongPasswordForAlice!"), role="reader")
        bob = User(email="bob@local.test", password_hash=hash_password("StrongPasswordForBob!!!"), role="reader")
        db.add_all((admin, alice, bob))
        db.commit()
        users = {u.email.split("@")[0]: u.id for u in (admin, alice, bob)}
    app = create_app(settings, sessions)
    with TestClient(app) as client:
        yield {"client": client, "settings": settings, "sessions": sessions,
               "users": users, "store": app.state.store}
    engine.dispose()


def access_token(client, email: str, password: str):
    res = client.post("/api/v1/auth/token", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture()
def tokens(context):
    client = context["client"]
    return {
        "admin": access_token(client, "admin@local.test", "StrongPasswordForAdmin!"),
        "alice": access_token(client, "alice@local.test", "StrongPasswordForAlice!"),
        "bob": access_token(client, "bob@local.test", "StrongPasswordForBob!!!"),
    }


def pdf_fixture(text="Секретний корпоративний контракт номер 123"):
    data = BytesIO()
    pdf = canvas.Canvas(data, pagesize=(595, 842))
    # ReportLab built-in Helvetica does not contain Cyrillic; use latin letters for text-extraction test.
    pdf.drawString(80, 740, "Secret corporate report 123, release plan stage three")
    pdf.showPage()
    pdf.save()
    return data.getvalue()


def blank_pdf_fixture():
    data = BytesIO()
    pdf = canvas.Canvas(data, pagesize=(595, 842))
    pdf.showPage()
    pdf.save()
    return data.getvalue()


def upload(client, headers, payload=None):
    return client.post("/api/v1/documents", headers=headers,
        data={"title": "Secret forecast", "classification": "confidential"},
        files={"file": ("report.pdf", payload or pdf_fixture(), "application/pdf")})
