"""add payout_line unique constraint

Revision ID: 3a9f2e1c8b05
Revises: 176dcec83dac
Create Date: 2026-04-25
"""
from alembic import op

revision = "3a9f2e1c8b05"
down_revision = "176dcec83dac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_payout_lines_run_artist",
        "payout_lines",
        ["payout_run_id", "artist_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_payout_lines_run_artist", "payout_lines", type_="unique")
