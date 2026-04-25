"""initial schema

Revision ID: 176dcec83dac
Revises:
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa

revision = "176dcec83dac"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("role", sa.Enum("owner", "manager", "staff", name="adminrole"), nullable=False, server_default="staff"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_admin_users_email", "admin_users", ["email"], unique=True)

    op.create_table(
        "artists",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(50)),
        sa.Column("bio", sa.Text),
        sa.Column("website", sa.String(500)),
        sa.Column("instagram", sa.String(200)),
        sa.Column("media_types", sa.String(500)),
        sa.Column("pos_vendor_name", sa.String(200)),
        sa.Column("status", sa.Enum("applicant", "active", "on_hold", "departed", name="artiststatus"), nullable=False, server_default="applicant"),
        sa.Column("w9_on_file", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("commission_rate_override", sa.String(10)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_artists_email", "artists", ["email"], unique=True)
    op.create_index("ix_artists_pos_vendor_name", "artists", ["pos_vendor_name"])

    op.create_table(
        "artist_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("artist_id", sa.String(36), sa.ForeignKey("artists.id"), nullable=False),
        sa.Column("magic_link_token", sa.String(200)),
        sa.Column("magic_link_expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_artist_users_artist_id", "artist_users", ["artist_id"], unique=True)
    op.create_index("ix_artist_users_magic_link_token", "artist_users", ["magic_link_token"])

    op.create_table(
        "agreements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("artist_id", sa.String(36), sa.ForeignKey("artists.id"), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(50)),
        sa.Column("agreement_html", sa.Text, nullable=False),
    )
    op.create_index("ix_agreements_artist_id", "agreements", ["artist_id"])

    op.create_table(
        "applications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(50)),
        sa.Column("bio", sa.Text),
        sa.Column("portfolio_url", sa.String(500)),
        sa.Column("media_types", sa.String(500)),
        sa.Column("artist_statement", sa.Text),
        sa.Column("status", sa.Enum("pending", "approved", "declined", "waitlisted", name="applicationstatus"), nullable=False, server_default="pending"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("admin_users.id")),
        sa.Column("notes", sa.Text),
    )
    op.create_index("ix_applications_email", "applications", ["email"])

    op.create_table(
        "booths",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("tier", sa.String(50), nullable=False),
        sa.Column("monthly_rate_cents", sa.Integer, nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_booths_name", "booths", ["name"], unique=True)

    op.create_table(
        "booth_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("booth_id", sa.String(36), sa.ForeignKey("booths.id"), nullable=False),
        sa.Column("artist_id", sa.String(36), sa.ForeignKey("artists.id"), nullable=False),
        sa.Column("started_at", sa.Date, nullable=False),
        sa.Column("ended_at", sa.Date),
    )
    op.create_index("ix_booth_assignments_booth_id", "booth_assignments", ["booth_id"])
    op.create_index("ix_booth_assignments_artist_id", "booth_assignments", ["artist_id"])

    op.create_table(
        "rent_charges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("artist_id", sa.String(36), sa.ForeignKey("artists.id"), nullable=False),
        sa.Column("booth_id", sa.String(36), sa.ForeignKey("booths.id"), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("amount_cents", sa.Integer, nullable=False),
        sa.Column("paid_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rent_charges_artist_id", "rent_charges", ["artist_id"])

    op.create_table(
        "sales",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("external_id", sa.String(200), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sales_external_id", "sales", ["external_id"], unique=True)
    op.create_index("ix_sales_occurred_at", "sales", ["occurred_at"])

    op.create_table(
        "payout_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("status", sa.Enum("draft", "reviewing", "sent", "complete", name="payoutrunstatus"), nullable=False, server_default="draft"),
        sa.Column("total_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "payout_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("payout_run_id", sa.String(36), sa.ForeignKey("payout_runs.id"), nullable=False),
        sa.Column("artist_id", sa.String(36), sa.ForeignKey("artists.id"), nullable=False),
        sa.Column("sales_total_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("commission_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("rent_deduction_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("net_cents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("method", sa.String(50)),
        sa.Column("external_id", sa.String(200)),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("error", sa.Text),
        sa.Column("settled_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_payout_lines_payout_run_id", "payout_lines", ["payout_run_id"])
    op.create_index("ix_payout_lines_artist_id", "payout_lines", ["artist_id"])
    op.create_index("ix_payout_lines_idempotency_key", "payout_lines", ["idempotency_key"], unique=True)

    op.create_table(
        "sale_line_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sale_id", sa.String(36), sa.ForeignKey("sales.id")),
        sa.Column("external_id", sa.String(200), nullable=False),
        sa.Column("order_external_id", sa.String(200), nullable=False),
        sa.Column("artist_id", sa.String(36), sa.ForeignKey("artists.id")),
        sa.Column("artist_external_id", sa.String(200), nullable=False),
        sa.Column("amount_cents", sa.Integer, nullable=False),
        sa.Column("commission_rate", sa.Numeric(5, 4), nullable=False),
        sa.Column("commission_cents", sa.Integer, nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("raw", sa.JSON, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payout_line_id", sa.String(36), sa.ForeignKey("payout_lines.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sale_line_items_external_id", "sale_line_items", ["external_id"], unique=True)
    op.create_index("ix_sale_line_items_sale_id", "sale_line_items", ["sale_id"])
    op.create_index("ix_sale_line_items_artist_id", "sale_line_items", ["artist_id"])
    op.create_index("ix_sale_line_items_artist_external_id", "sale_line_items", ["artist_external_id"])
    op.create_index("ix_sale_line_items_occurred_at", "sale_line_items", ["occurred_at"])
    op.create_index("ix_sale_line_items_payout_line_id", "sale_line_items", ["payout_line_id"])

    op.create_table(
        "sync_cursors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sync_cursors_provider", "sync_cursors", ["provider"], unique=True)

    op.create_table(
        "error_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event", sa.String(200), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("details", sa.JSON),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_error_logs_event", "error_logs", ["event"])
    op.create_index("ix_error_logs_created_at", "error_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("error_logs")
    op.drop_table("sync_cursors")
    op.drop_table("sale_line_items")
    op.drop_table("payout_lines")
    op.drop_table("payout_runs")
    op.drop_table("sales")
    op.drop_table("rent_charges")
    op.drop_table("booth_assignments")
    op.drop_table("booths")
    op.drop_table("applications")
    op.drop_table("agreements")
    op.drop_table("artist_users")
    op.drop_table("artists")
    op.drop_table("admin_users")
    op.execute("DROP TYPE IF EXISTS adminrole")
    op.execute("DROP TYPE IF EXISTS artiststatus")
    op.execute("DROP TYPE IF EXISTS applicationstatus")
    op.execute("DROP TYPE IF EXISTS payoutrunstatus")
