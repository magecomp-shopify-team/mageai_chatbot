"""add comment column to session_reviews

Revision ID: 004
Revises: 003
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("session_reviews", sa.Column("comment", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("session_reviews", "comment")
