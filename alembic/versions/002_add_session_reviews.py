"""add session_reviews table

Revision ID: 002
Revises: 001
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_reviews",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(128), nullable=False),
        sa.Column("app_id", sa.String(64), nullable=False),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("emoji_label", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_review_session_app", "session_reviews", ["session_id", "app_id"])


def downgrade() -> None:
    op.drop_index("idx_review_session_app", table_name="session_reviews")
    op.drop_table("session_reviews")
