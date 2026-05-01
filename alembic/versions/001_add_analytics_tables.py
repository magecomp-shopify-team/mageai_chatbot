"""add analytics tables

Revision ID: 001
Revises: 000
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = "000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("app_id", sa.String(64), nullable=False),
        sa.Column("external_user_id", sa.String(256), nullable=True),
        sa.Column("name", sa.String(256), nullable=True),
        sa.Column("email", sa.String(256), nullable=True),
        sa.Column("business_name", sa.String(256), nullable=True),
        sa.Column("extra_metadata", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("last_seen_at", sa.DateTime, nullable=False),
    )
    op.create_index(
        "idx_user_app_external",
        "user_profiles",
        ["app_id", "external_user_id"],
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(128), nullable=False),
        sa.Column("app_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user_profiles.id"), nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("last_active_at", sa.DateTime, nullable=False),
        sa.Column("ended_at", sa.DateTime, nullable=True),
        sa.Column("entry_url", sa.String(2048), nullable=True),
        sa.Column("exit_url", sa.String(2048), nullable=True),
        sa.Column("device_type", sa.String(64), nullable=True),
        sa.Column("browser", sa.String(128), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("message_count", sa.Integer, nullable=False, default=0),
        sa.Column("extra_metadata", sa.Text, nullable=True),
    )
    op.create_index(
        "idx_chat_session_app",
        "chat_sessions",
        ["session_id", "app_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_chat_session_app", table_name="chat_sessions")
    op.drop_table("chat_sessions")
    op.drop_index("idx_user_app_external", table_name="user_profiles")
    op.drop_table("user_profiles")
