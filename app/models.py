"""Authoritative metadata and ACL models. All identifiers are unguessable UUID strings."""
from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Integer, Text, UniqueConstraint, Index,
    CheckConstraint, Boolean,
)
from .db import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=new_id)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False, default="reader")
    is_active = Column(Boolean, nullable=False, default=True)
    token_version = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (CheckConstraint("role IN ('admin','reader')", name="ck_users_role"),)


class Group(Base):
    __tablename__ = "groups"
    id = Column(String(36), primary_key=True, default=new_id)
    name = Column(String(100), nullable=False, unique=True)


class GroupMembership(Base):
    __tablename__ = "group_memberships"
    group_id = Column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class Document(Base):
    __tablename__ = "documents"
    id = Column(String(36), primary_key=True, default=new_id)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(180), nullable=False)
    classification = Column(String(20), nullable=False, default="internal")
    acl_epoch = Column(Integer, nullable=False, default=0)
    active_index_run_id = Column(String(36), nullable=True)  # Stage 4 publication
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (
        CheckConstraint("classification IN ('internal','confidential')", name="ck_docs_classification"),
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(String(36), primary_key=True, default=new_id)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    sha256 = Column(String(64), nullable=False)
    byte_size = Column(Integer, nullable=False)
    object_key = Column(String(200), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (UniqueConstraint("document_id", "sha256", name="uq_document_checksum"),)


class AccessGrant(Base):
    __tablename__ = "access_grants"
    id = Column(String(36), primary_key=True, default=new_id)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    principal_type = Column(String(10), nullable=False)
    principal_id = Column(String(36), nullable=False)
    permission = Column(String(8), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("document_id", "principal_type", "principal_id", "permission", name="uq_grant"),
        CheckConstraint("principal_type IN ('user','group')", name="ck_grants_principal_type"),
        CheckConstraint("permission IN ('read','write','admin')", name="ck_grants_permission"),
        Index("ix_grants_lookup", "principal_type", "principal_id", "document_id"),
    )


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    id = Column(String(36), primary_key=True, default=new_id)
    version_id = Column(String(36), ForeignKey("document_versions.id"), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="PENDING")
    attempts = Column(Integer, nullable=False, default=0)
    lease_until = Column(DateTime(timezone=True), nullable=True)
    failure_code = Column(String(60), nullable=True)
    index_run_id = Column(String(36), nullable=True)  # Stage 4, NULL until indexed
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    __table_args__ = (Index("ix_job_queue", "status", "lease_until"),)


class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(String(36), primary_key=True, default=new_id)
    version_id = Column(String(36), ForeignKey("document_versions.id"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    ordinal = Column(Integer, nullable=False)
    text_object_key = Column(String(200), nullable=False)
    index_run_id = Column(String(36), nullable=True)  # Stage 4
    __table_args__ = (UniqueConstraint("version_id", "ordinal", name="uq_version_ordinal"),)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(String(36), primary_key=True, default=new_id)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(60), nullable=False)
    decision = Column(String(10), nullable=False)
    target_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    # no raw document text, prompt, bearer token, or password
