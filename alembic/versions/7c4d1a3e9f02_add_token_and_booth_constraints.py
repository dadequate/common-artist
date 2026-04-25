"""add token and booth assignment constraints

Revision ID: 7c4d1a3e9f02
Revises: 3a9f2e1c8b05
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "7c4d1a3e9f02"
down_revision = "3a9f2e1c8b05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Unique on magic_link_token -- PostgreSQL allows multiple NULLs under UNIQUE
    op.create_index(
        "ix_artist_users_magic_link_token_unique",
        "artist_users",
        ["magic_link_token"],
        unique=True,
        postgresql_where=sa.text("magic_link_token IS NOT NULL"),
    )

    # Prevent two active assignments for the same booth
    op.create_index(
        "ix_booth_assignments_active_booth",
        "booth_assignments",
        ["booth_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_booth_assignments_active_booth", "booth_assignments")
    op.drop_index("ix_artist_users_magic_link_token_unique", "artist_users")
