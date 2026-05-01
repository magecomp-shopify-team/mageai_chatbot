"""baseline existing tables

Revision ID: 000
Revises:
Create Date: 2026-04-21

This migration is a no-op. The tables it covers (admin_users, audit_log,
conversation_turns) were created before Alembic was introduced via
SQLAlchemy create_all(). Stamping them here lets Alembic track the full
history without re-creating tables that already exist.
"""
from alembic import op
import sqlalchemy as sa

revision = "000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables already exist — nothing to do.
    pass


def downgrade() -> None:
    op.drop_index("idx_session_app", table_name="conversation_turns")
    op.drop_table("conversation_turns")
    op.drop_table("audit_log")
    op.drop_table("admin_users")
