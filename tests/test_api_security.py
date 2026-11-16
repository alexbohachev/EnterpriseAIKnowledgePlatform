import jwt
from app.models import Document
from .conftest import upload


def test_auth_without_token_and_forged_token(context, tokens):
    c = context["client"]
    assert c.get("/api/v1/auth/me").status_code == 401
    assert c.post("/api/v1/auth/token", json={"email":"bob@local.test", "password":"wrong"}).status_code == 401
    assert c.get("/api/v1/auth/me", headers={"Authorization": "Bearer forged"}).status_code == 401
    valid = tokens["bob"]["Authorization"].split(" ")[1]
    forged_data = jwt.decode(valid, context["settings"].jwt_secret, algorithms=["HS256"],
                             audience=context["settings"].jwt_audience,
                             issuer=context["settings"].jwt_issuer)
    forged_data["sub"] = context["users"]["admin"]
    tampered = jwt.encode(forged_data, "a-different-secret-not-the-real-key-00000", algorithm="HS256")
    assert c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401


def test_upload_metadata_acl_and_revoke(context, tokens):
    c = context["client"]
    res = upload(c, tokens["alice"])
    assert res.status_code == 202, res.text
    doc, job = res.json()["document_id"], res.json()["job_id"]
    assert res.json()["status"] == "PENDING"
    assert c.get(f"/api/v1/documents/{doc}", headers=tokens["bob"]).status_code == 404
    assert c.get(f"/api/v1/jobs/{job}", headers=tokens["bob"]).status_code == 404
    assert c.get(f"/api/v1/documents/{doc}/download", headers=tokens["bob"]).status_code == 404
    assert c.get("/api/v1/documents", headers=tokens["bob"]).json() == []
    assert c.get(f"/api/v1/documents/{doc}", headers=tokens["alice"]).status_code == 200
    assert c.get(f"/api/v1/documents/{doc}/download", headers=tokens["alice"]).content.startswith(b"%PDF-")
    assert c.get(f"/api/v1/jobs/{job}", headers=tokens["alice"]).status_code == 200

    acl = {"action": "grant", "principal_type": "user", "principal_id": context["users"]["bob"], "permission": "read"}
    # Bob cannot grant permissions to himself.
    assert c.post(f"/api/v1/documents/{doc}/acl", headers=tokens["bob"], json=acl).status_code == 404
    allow = c.post(f"/api/v1/documents/{doc}/acl", headers=tokens["alice"], json=acl)
    assert allow.status_code == 200 and allow.json()["changed"]
    assert allow.json()["acl_epoch"] == 1
    assert c.get(f"/api/v1/documents/{doc}", headers=tokens["bob"]).status_code == 200
    assert c.get(f"/api/v1/jobs/{job}", headers=tokens["bob"]).status_code == 404  # read != write
    assert c.post(f"/api/v1/documents/{doc}/acl", headers=tokens["alice"], json=acl).json()["changed"] is False
    acl["action"] = "revoke"
    deny = c.post(f"/api/v1/documents/{doc}/acl", headers=tokens["alice"], json=acl)
    assert deny.status_code == 200 and deny.json()["acl_epoch"] == 2
    assert c.get(f"/api/v1/documents/{doc}", headers=tokens["bob"]).status_code == 404
    assert c.get(f"/api/v1/documents/{doc}/download", headers=tokens["bob"]).status_code == 404
    assert c.get(f"/api/v1/documents/{doc}", headers=tokens["admin"]).status_code == 200
    with context["sessions"]() as db:
        assert db.get(Document, doc).active_index_run_id is None


def test_body_cannot_override_identity(context, tokens):
    c = context["client"]
    doc = upload(c, tokens["alice"]).json()["document_id"]
    # API ignores supplied role/user_id even if JSON includes them.
    ret = c.post(f"/api/v1/documents/{doc}/acl", headers=tokens["bob"], json={
        "action": "grant", "principal_type": "user", "principal_id": context["users"]["bob"],
        "permission": "read", "user_id": context["users"]["admin"], "role": "admin"})
    assert ret.status_code == 404
    # Offline GraphRAG fails closed without configured real services.
    q = c.post("/api/v1/query", headers=tokens["alice"], json={"question": "Explain the document"})
    assert q.status_code == 503
    assert c.post("/api/v1/query", json={"question": "Explain the document"}).status_code == 401


def test_group_permission_and_revocation(context, tokens):
    c = context["client"]
    doc = upload(c, tokens["alice"]).json()["document_id"]
    grp = c.post("/api/v1/groups", headers=tokens["admin"], json={"name": "finance"})
    assert grp.status_code == 201
    group_id = grp.json()["id"]
    membership = c.post(f"/api/v1/groups/{group_id}/members", headers=tokens["admin"],
                        json={"user_id": context["users"]["bob"]})
    assert membership.status_code == 201
    acl = {"action": "grant", "principal_type":"group", "principal_id":group_id, "permission":"read"}
    assert c.post(f"/api/v1/documents/{doc}/acl", headers=tokens["alice"], json=acl).status_code == 200
    before_leave = c.get(f"/api/v1/documents/{doc}", headers=tokens["bob"])
    assert before_leave.status_code == 200
    epoch_before = before_leave.json()["acl_epoch"]
    assert c.delete(f"/api/v1/groups/{group_id}/members/{context['users']['bob']}",
                    headers=tokens["admin"]).status_code == 204
    assert c.get(f"/api/v1/documents/{doc}", headers=tokens["bob"]).status_code == 404
    assert c.get(f"/api/v1/documents/{doc}", headers=tokens["alice"]).json()["acl_epoch"] == epoch_before + 1


def test_upload_validation(context, tokens):
    c = context["client"]
    wrong = c.post("/api/v1/documents", headers=tokens["alice"], data={"title": "x"},
                   files={"file": ("evil.pdf", b"not pdf", "application/pdf")})
    assert wrong.status_code == 415
    wrong_extension = c.post("/api/v1/documents", headers=tokens["alice"], data={"title": "x"},
                   files={"file": ("evil.bin", b"%PDF-foobar", "application/pdf")})
    assert wrong_extension.status_code == 415
    huge = c.post("/api/v1/documents", headers=tokens["alice"], data={"title": "x"},
                  files={"file": ("huge.pdf", b"%PDF-" + b"x" * (12 * 1024 * 1024), "application/pdf")})
    assert huge.status_code == 413
