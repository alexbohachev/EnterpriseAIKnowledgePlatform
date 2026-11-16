"""EAKP Stage 6 HTTP API with opt-in local telemetry. No external AI fallback."""
from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
import hmac
import time
import uuid
from fastapi import (FastAPI, Depends, File, Form, HTTPException, UploadFile, Request, status)
from fastapi.responses import Response
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import Settings
from .db import make_session_factory
from .models import (User, Group, GroupMembership, Document, DocumentVersion,
                     AccessGrant, IngestionJob, AuditEvent)
from .schemas import (LoginRequest, LoginResponse, UserResponse, UserCreate, GroupCreate,
                      MemberCreate, UploadResponse, DocumentResponse, JobResponse,
                      ACLChange, ACLChangeResponse, QueryInput, QueryResponse)
from .security import (hash_password, verify_password, issue_token, db_session, current_user,
                       require_admin, get_visible_doc, allowed, settings_dep, DUMMY_PASSWORD_HASH)
from .storage import LocalStorage
from .ratelimit import InProcessRateLimiter
from .guardrails import UnsafeInput, UnsafeModelOutput, guard_question
from .observability import Observability, safe_route, CONTENT_TYPE_LATEST, configure_tracing


def create_app(settings: Settings | None = None, session_factory=None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Enterprise AI Knowledge Platform", version="0.6.0",
                  description="Stage 6: local GraphRAG with observability (MVP, not certified).")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[h.strip() for h in settings.allowed_http_hosts.split(",") if h.strip()])
    if session_factory is None:
        engine, session_factory = make_session_factory(settings.database_url)
        app.state.db_engine = engine
    app.state.session_factory = session_factory
    app.state.settings = settings
    app.state.store = LocalStorage(settings.storage_root)
    app.state.rag_engine = None  # injectable in tests; lazy production initialization
    app.state.limiter = InProcessRateLimiter()
    app.state.observability = Observability()
    configure_tracing(settings.otlp_traces_endpoint)

    @app.middleware("http")
    async def secure_headers(request: Request, call_next):
        # Metrics use low-cardinality route *templates*, not arbitrary URL paths.
        observer = app.state.observability
        observer.inflight.inc()
        started = time.perf_counter()
        code = 500
        with trace.get_tracer("eakp.api").start_as_current_span("http.server", kind=SpanKind.SERVER) as span:
            span.set_attribute("http.request.method", request.method)
            try:
                response = await call_next(request)
                code = response.status_code
            finally:
                observer.inflight.dec()
                route_obj = request.scope.get("route")
                route = safe_route(getattr(route_obj, "path", None))
                span.set_attribute("http.route", route)
                span.set_attribute("http.response.status_code", code)
                if route != "/internal/metrics":
                    observer.requests.labels(method=request.method, route=route,
                                              status_class=f"{code // 100}xx").inc()
                    observer.duration.labels(method=request.method, route=route).observe(
                        time.perf_counter() - started)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Request-ID"] = str(uuid.uuid4())
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.get("/healthz")
    def health():
        return {"status": "alive", "stage": 6}

    @app.get("/internal/metrics", include_in_schema=False)
    def prometheus_metrics(request: Request):
        # Disabled by default; monitoring runs through a dedicated long-lived secret.
        # Endpoint and secret must also be restricted at ingress and firewall.
        token = app.state.settings.metrics_token
        if not token:
            raise HTTPException(404, "Not found")
        auth = request.headers.get("Authorization", "")
        expected = f"Bearer {token}"
        if not hmac.compare_digest(auth.encode(), expected.encode()):
            raise HTTPException(403, "Forbidden")
        return Response(content=app.state.observability.render(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/readyz")
    def ready(db: Session = Depends(db_session)):
        try:
            db.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Database unavailable")

    @app.post("/api/v1/auth/token", response_model=LoginResponse)
    def login(payload: LoginRequest, request: Request, db: Session = Depends(db_session),
              cfg: Settings = Depends(settings_dep)):
        # Trust socket peer, NOT user-supplied X-Forwarded-For.
        peer = request.client.host if request.client else "unknown"
        app.state.limiter.check("login", peer, cfg.login_max_per_minute)
        email = payload.email.strip().lower()
        user = db.scalar(select(User).where(User.email == email))
        # Avoid revealing whether email exists. Rate limiting is enforced above.
        # Always perform an Argon2 check; avoid easy user-enumeration timing signals.
        digest = user.password_hash if user and user.is_active else DUMMY_PASSWORD_HASH
        is_correct = verify_password(payload.password, digest)
        if not user or not user.is_active or not is_correct:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        return LoginResponse(access_token=issue_token(user.id, cfg, user.token_version))

    @app.post("/api/v1/auth/logout-all")
    def logout_all(user: User = Depends(current_user), db: Session = Depends(db_session)):
        current = db.scalar(select(User).where(User.id == user.id).with_for_update())
        current.token_version += 1
        db.add(AuditEvent(actor_id=user.id, action="tokens_revoked", decision="allow", target_id=user.id))
        db.commit()
        return {"revoked": True}

    @app.post("/api/v1/users/{user_id}/revoke-tokens")
    def admin_revoke_tokens(user_id: str, db: Session = Depends(db_session),
                            admin: User = Depends(require_admin)):
        target = db.scalar(select(User).where(User.id == user_id).with_for_update())
        if not target:
            raise HTTPException(404, "User not found")
        target.token_version += 1
        db.add(AuditEvent(actor_id=admin.id, action="tokens_revoked", decision="allow", target_id=user_id))
        db.commit()
        return {"revoked": True}

    @app.get("/api/v1/auth/me", response_model=UserResponse)
    def me(user: User = Depends(current_user)):
        return user

    @app.post("/api/v1/users", status_code=201, response_model=UserResponse)
    def create_user(payload: UserCreate, db: Session = Depends(db_session),
                    _admin: User = Depends(require_admin)):
        user = User(email=payload.email.strip().lower(), password_hash=hash_password(payload.password),
                    role=payload.role)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "User already exists")
        db.refresh(user)
        return user

    def bump_acl_for_group(db: Session, group_id: str) -> None:
        """Membership changes invalidate ACL snapshots of group-shared documents."""
        doc_ids = db.scalars(select(AccessGrant.document_id).where(
            AccessGrant.principal_type == "group", AccessGrant.principal_id == group_id,
            AccessGrant.revoked_at.is_(None)).distinct()).all()
        for doc_id in sorted(doc_ids):
            doc = db.scalar(select(Document).where(Document.id == doc_id).with_for_update())
            if doc:
                doc.acl_epoch += 1

    @app.post("/api/v1/groups", status_code=201)
    def create_group(payload: GroupCreate, db: Session = Depends(db_session),
                     _admin: User = Depends(require_admin)):
        group = Group(name=payload.name)
        db.add(group)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "Group name already exists")
        return {"id": group.id, "name": group.name}

    @app.post("/api/v1/groups/{group_id}/members", status_code=201)
    def add_group_member(group_id: str, payload: MemberCreate,
                         db: Session = Depends(db_session), _admin: User = Depends(require_admin)):
        if not db.get(Group, group_id) or not db.get(User, payload.user_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Group or user not found")
        existing = db.get(GroupMembership, (group_id, payload.user_id))
        if existing is None:
            db.add(GroupMembership(group_id=group_id, user_id=payload.user_id))
            bump_acl_for_group(db, group_id)
            db.commit()
        return {"group_id": group_id, "user_id": payload.user_id}

    @app.delete("/api/v1/groups/{group_id}/members/{user_id}", status_code=204)
    def remove_group_member(group_id: str, user_id: str, db: Session = Depends(db_session),
                            _admin: User = Depends(require_admin)):
        membership = db.get(GroupMembership, (group_id, user_id))
        if membership:
            db.delete(membership)
            # Group membership revoke must take effect immediately, including epoch invalidation.
            bump_acl_for_group(db, group_id)
            db.commit()
        return Response(status_code=204)

    @app.post("/api/v1/documents", status_code=202, response_model=UploadResponse)
    def upload_document(file: UploadFile = File(...), title: str = Form(..., min_length=1, max_length=180),
                        classification: str = Form("internal"),
                        db: Session = Depends(db_session), user: User = Depends(current_user),
                        cfg: Settings = Depends(settings_dep)):
        app.state.limiter.check("upload", user.id, cfg.upload_max_per_minute)
        if classification not in ("internal", "confidential"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid classification")
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "PDF filename required")
        store = app.state.store
        # Writes to a random server-generated filename and enforces a hard byte cap.
        key, length, digest = store.save_pdf(file, cfg.max_upload_mb * 1024 * 1024)
        try:
            doc = Document(owner_id=user.id, title=title, classification=classification)
            db.add(doc)
            db.flush()
            version = DocumentVersion(document_id=doc.id, object_key=key, sha256=digest,
                                      byte_size=length)
            db.add(version)
            db.flush()
            job = IngestionJob(version_id=version.id, status="PENDING")
            db.add(job)
            db.add(AuditEvent(actor_id=user.id, action="document_upload", decision="allow", target_id=doc.id))
            db.commit()
        except Exception:
            db.rollback()
            store.delete(key)
            raise
        return UploadResponse(document_id=doc.id, version_id=version.id,
                              job_id=job.id, status=job.status)

    @app.get("/api/v1/documents", response_model=list[DocumentResponse])
    def list_documents(db: Session = Depends(db_session), user: User = Depends(current_user)):
        # Bounded MVP dataset. Replace scan with indexed SQL ACL join when scaling.
        docs = db.scalars(select(Document).order_by(Document.created_at.desc()).limit(1000)).all()
        return [d for d in docs if allowed(db, user, d, "read")]

    @app.get("/api/v1/documents/{document_id}", response_model=DocumentResponse)
    def get_document(document_id: str, db: Session = Depends(db_session),
                     user: User = Depends(current_user)):
        return get_visible_doc(db, user, document_id)

    @app.get("/api/v1/documents/{document_id}/download")
    def download_document(document_id: str, db: Session = Depends(db_session),
                          user: User = Depends(current_user)):
        doc = get_visible_doc(db, user, document_id, "read")
        version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
                            .order_by(DocumentVersion.created_at.desc()))
        if not version:
            raise HTTPException(404, "File unavailable")
        path = app.state.store.path(version.object_key)
        if not path.is_file():
            raise HTTPException(503, "File unavailable")
        # This small-file MVP buffers the PDF and never serves direct object-storage URLs.
        # This cannot guarantee revoke safety after network transmission starts.
        content = path.read_bytes()
        # Recheck current authoritative ACL just before composing the response.
        db.expire_all()
        doc = get_visible_doc(db, user, document_id, "read")
        return Response(content=content, media_type="application/pdf",
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                                 "Content-Disposition": "attachment; filename=report.pdf"})

    @app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
    def job_status(job_id: str, db: Session = Depends(db_session),
                   user: User = Depends(current_user)):
        job = db.get(IngestionJob, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        version = db.get(DocumentVersion, job.version_id)
        get_visible_doc(db, user, version.document_id, "write")
        return job

    @app.post("/api/v1/documents/{document_id}/acl", response_model=ACLChangeResponse)
    def change_acl(document_id: str, payload: ACLChange, db: Session = Depends(db_session),
                   user: User = Depends(current_user)):
        # Lock document row in PostgreSQL while serializing ACL writes and epoch changes.
        doc = db.scalar(select(Document).where(Document.id == document_id).with_for_update())
        if not doc or not allowed(db, user, doc, "admin"):
            raise HTTPException(404, "Document not found")
        principal = db.get(User if payload.principal_type == "user" else Group,
                           payload.principal_id)
        if not principal:
            raise HTTPException(404, "Principal not found")
        stmt = select(AccessGrant).where(AccessGrant.document_id == doc.id,
                                        AccessGrant.principal_type == payload.principal_type,
                                        AccessGrant.principal_id == payload.principal_id,
                                        AccessGrant.permission == payload.permission)
        grant = db.scalar(stmt)
        changed = False
        if payload.action == "grant":
            if grant is None:
                db.add(AccessGrant(document_id=doc.id, principal_type=payload.principal_type,
                                   principal_id=payload.principal_id, permission=payload.permission))
                changed = True
            elif grant.revoked_at is not None:
                grant.revoked_at = None
                changed = True
        elif grant is not None and grant.revoked_at is None:
            from .models import utc_now
            grant.revoked_at = utc_now()
            changed = True
        if changed:
            doc.acl_epoch += 1
            db.add(AuditEvent(actor_id=user.id, action=f"acl_{payload.action}",
                              decision="allow", target_id=doc.id))
            db.commit()
        return ACLChangeResponse(document_id=doc.id, acl_epoch=doc.acl_epoch, changed=changed)

    @app.post("/api/v1/query", response_model=QueryResponse)
    def query(payload: QueryInput, db: Session = Depends(db_session),
              user: User = Depends(current_user), cfg: Settings = Depends(settings_dep)):
        app.state.limiter.check("query", user.id, cfg.query_max_per_minute)
        try:
            safe_question = guard_question(payload.question)
        except UnsafeInput:
            raise HTTPException(422, "Request violates input policy")
        from .rag.backends import BackendUnavailable, OllamaLocal, QdrantLocal, Neo4jLocal
        from .rag.query import QueryEngine, AuthorizationChanged
        from .rag.workflow import build_langgraph
        if not payload.question.strip():
            raise HTTPException(422, "Question must not be blank")
        try:
            if app.state.rag_engine is None:
                if len(cfg.neo4j_password) < 12:
                    raise BackendUnavailable("Neo4j credentials are not configured")
                local = OllamaLocal(cfg.ollama_url, cfg.embedding_model, cfg.chat_model)
                vector = QdrantLocal(cfg.qdrant_url, cfg.qdrant_collection, cfg.embedding_dim)
                graph = Neo4jLocal(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
                app.state.rag_engine = QueryEngine(local, vector, graph, local, app.state.store)
            workflow = build_langgraph(app.state.rag_engine, db, user, app.state.observability)
            result = workflow.invoke({"user_id": user.id, "question": safe_question})["result"]
            return QueryResponse(answer=result.answer, citations=result.citations,
                                 retrieval_count=result.retrieval_count)
        except AuthorizationChanged:
            raise HTTPException(409, "Permissions changed during request; retry")
        except UnsafeInput:
            raise HTTPException(422, "Request violates input policy")
        except UnsafeModelOutput:
            raise HTTPException(502, "Invalid local model output")
        except BackendUnavailable:
            raise HTTPException(503, "Local AI or index service unavailable")
        except (ValueError, OSError):
            raise HTTPException(503, "Local AI retrieval failed")

    return app


app = create_app()
