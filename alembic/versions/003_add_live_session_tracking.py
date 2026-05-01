"""add live session tracking columns

Revision ID: 003
Revises: 002
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("is_live", sa.Boolean, nullable=False, server_default="0"))
    op.add_column("chat_sessions", sa.Column("closed_at", sa.DateTime, nullable=True))


def downgrade() -> None:
    op.drop_column("chat_sessions", "closed_at")
    op.drop_column("chat_sessions", "is_live")
