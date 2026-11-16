from datetime import datetime, timedelta, timezone
from uuid import uuid4
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .models import User, GroupMembership, AccessGrant, Document

_passwords = PasswordHasher(time_cost=2, memory_cost=32768, parallelism=2)
_bearer = HTTPBearer(auto_error=False)
# Argon2 dummy check for unknown accounts; computed once at startup.
DUMMY_PASSWORD_HASH = _passwords.hash("This account does not exist. XX-2026-0123!")


def hash_password(password: str) -> str:
    if len(password) < 12 or len(password) > 128:
        raise ValueError("Password must contain 12..128 characters")
    return _passwords.hash(password)


def verify_password(password: str, digest: str) -> bool:
    try:
        return _passwords.verify(digest, password)
    except (VerifyMismatchError, VerificationError):
        return False


def issue_token(user_id: str, settings, token_version: int = 0) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iss": settings.jwt_issuer, "aud": settings.jwt_audience,
               "iat": now, "nbf": now, "exp": now + timedelta(minutes=settings.jwt_minutes),
               "jti": str(uuid4()), "ver": token_version}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def db_session(request: Request):
    with request.app.state.session_factory() as session:
        yield session


def settings_dep(request: Request):
    return request.app.state.settings


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
                 session: Session = Depends(db_session), settings=Depends(settings_dep)) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        data = jwt.decode(credentials.credentials, settings.jwt_secret,
                          algorithms=["HS256"], audience=settings.jwt_audience,
                          issuer=settings.jwt_issuer, options={"require": ["sub", "exp", "iat", "nbf", "iss", "aud", "ver"]})
        user = session.get(User, data["sub"])
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid bearer token")
    if not user or not user.is_active or data["ver"] != user.token_version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown or disabled user")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin required")
    return user


_LEVELS = {"read": 1, "write": 2, "admin": 3}


def allowed(session: Session, user: User, doc: Document, permission="read") -> bool:
    if not user.is_active:
        return False
    if user.role == "admin" or doc.owner_id == user.id:
        return True
    groups = {member.group_id for member in session.query(GroupMembership).filter_by(user_id=user.id)}
    grants = session.query(AccessGrant).filter_by(document_id=doc.id, revoked_at=None).all()
    return any((_LEVELS[g.permission] >= _LEVELS[permission] and
                ((g.principal_type == "user" and g.principal_id == user.id) or
                 (g.principal_type == "group" and g.principal_id in groups))) for g in grants)


def get_visible_doc(session: Session, user: User, doc_id: str, permission="read") -> Document:
    doc = session.get(Document, doc_id)
    if not doc or not allowed(session, user, doc, permission):
        # Hide existence of documents for unauthorized principals.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return doc
