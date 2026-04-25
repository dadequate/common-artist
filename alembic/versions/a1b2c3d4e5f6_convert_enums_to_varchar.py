"""convert native enum columns to varchar

Revision ID: a1b2c3d4e5f6
Revises: 7c4d1a3e9f02
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "7c4d1a3e9f02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE artists ALTER COLUMN status TYPE VARCHAR(50) USING status::text")
    op.execute("ALTER TABLE applications ALTER COLUMN status TYPE VARCHAR(50) USING status::text")
    op.execute("ALTER TABLE payout_runs ALTER COLUMN status TYPE VARCHAR(50) USING status::text")
    op.execute("ALTER TABLE admin_users ALTER COLUMN role TYPE VARCHAR(50) USING role::text")

    op.execute("DROP TYPE IF EXISTS artiststatus CASCADE")
    op.execute("DROP TYPE IF EXISTS applicationstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS payoutrunstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS adminrole CASCADE")


def downgrade() -> None:
    op.execute("CREATE TYPE artiststatus AS ENUM ('applicant', 'active', 'on_hold', 'departed')")
    op.execute("ALTER TABLE artists ALTER COLUMN status TYPE artiststatus USING status::artiststatus")

    op.execute("CREATE TYPE applicationstatus AS ENUM ('pending', 'approved', 'declined', 'waitlisted')")
    op.execute("ALTER TABLE applications ALTER COLUMN status TYPE applicationstatus USING status::applicationstatus")

    op.execute("CREATE TYPE payoutrunstatus AS ENUM ('draft', 'reviewing', 'sent', 'complete')")
    op.execute("ALTER TABLE payout_runs ALTER COLUMN status TYPE payoutrunstatus USING status::payoutrunstatus")

    op.execute("CREATE TYPE adminrole AS ENUM ('owner', 'manager', 'staff')")
    op.execute("ALTER TABLE admin_users ALTER COLUMN role TYPE adminrole USING role::adminrole")
