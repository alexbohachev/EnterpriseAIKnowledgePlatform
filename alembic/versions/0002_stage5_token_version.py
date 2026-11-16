"""Stage 5 token invalidation counter.

Revision ID: 0002_stage5
Revises: 0001_stage3
"""
from alembic import op
import sqlalchemy as sa
revision = "0002_stage5"
down_revision = "0001_stage3"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))

def downgrade():
    op.drop_column("users", "token_version")
