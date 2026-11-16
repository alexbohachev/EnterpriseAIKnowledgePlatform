"""Initial Stage 3 SQL schema (matches SQLAlchemy models).

Revision ID: 0001_stage3
Revises:
"""
from alembic import op
import sqlalchemy as sa
revision = "0001_stage3"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('admin','reader')", name="ck_users_role"),
        sa.UniqueConstraint("email"))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("groups", sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False), sa.UniqueConstraint("name"))
    op.create_table("group_memberships",
        sa.Column("group_id", sa.String(36), sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("classification", sa.String(20), nullable=False),
        sa.Column("acl_epoch", sa.Integer(), nullable=False),
        sa.Column("active_index_run_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("classification IN ('internal','confidential')", name="ck_docs_classification"))
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])
    op.create_table("document_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("object_key"),
        sa.UniqueConstraint("document_id", "sha256", name="uq_document_checksum"))
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_table("access_grants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("principal_type", sa.String(10), nullable=False),
        sa.Column("principal_id", sa.String(36), nullable=False),
        sa.Column("permission", sa.String(8), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("principal_type IN ('user','group')", name="ck_grants_principal_type"),
        sa.CheckConstraint("permission IN ('read','write','admin')", name="ck_grants_permission"),
        sa.UniqueConstraint("document_id", "principal_type", "principal_id", "permission", name="uq_grant"))
    op.create_index("ix_access_grants_document_id", "access_grants", ["document_id"])
    op.create_index("ix_grants_lookup", "access_grants", ["principal_type", "principal_id", "document_id"])
    op.create_table("ingestion_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("failure_code", sa.String(60)),
        sa.Column("index_run_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("version_id"))
    op.create_index("ix_job_queue", "ingestion_jobs", ["status", "lease_until"])
    op.create_table("chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text_object_key", sa.String(200), nullable=False),
        sa.Column("index_run_id", sa.String(36)),
        sa.UniqueConstraint("version_id", "ordinal", name="uq_version_ordinal"))
    op.create_index("ix_chunks_version_id", "chunks", ["version_id"])
    op.create_table("audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("decision", sa.String(10), nullable=False),
        sa.Column("target_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    for name in ("audit_events", "chunks", "ingestion_jobs", "access_grants",
                 "document_versions", "documents", "group_memberships", "groups", "users"):
        op.drop_table(name)
