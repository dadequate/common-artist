import uuid
from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PayoutRunStatus(str, PyEnum):
    DRAFT     = "draft"
    REVIEWING = "reviewing"
    SENT      = "sent"
    COMPLETE  = "complete"


class PayoutLine(Base):
    __tablename__ = "payout_lines"

    id:                   Mapped[str]             = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payout_run_id:        Mapped[str]             = mapped_column(ForeignKey("payout_runs.id"), index=True)
    artist_id:            Mapped[str]             = mapped_column(ForeignKey("artists.id"), index=True)
    sales_total_cents:    Mapped[int]             = mapped_column(Integer, default=0)
    commission_cents:     Mapped[int]             = mapped_column(Integer, default=0)
    rent_deduction_cents: Mapped[int]             = mapped_column(Integer, default=0)
    net_cents:            Mapped[int]             = mapped_column(Integer, default=0)
    status:               Mapped[str]             = mapped_column(String(50), default="pending")
    method:               Mapped[str | None]      = mapped_column(String(50))
    external_id:          Mapped[str | None]      = mapped_column(String(200))
    idempotency_key:      Mapped[str]             = mapped_column(String(200), unique=True, default=lambda: str(uuid.uuid4()))
    error:                Mapped[str | None]      = mapped_column(Text)
    settled_at:           Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    payout_run: Mapped["PayoutRun"]        = relationship("PayoutRun", back_populates="lines")
    artist:     Mapped["Artist"]           = relationship("Artist", back_populates="payout_lines")  # noqa: F821
    sale_items: Mapped[list["SaleLineItem"]] = relationship("SaleLineItem", back_populates="payout_line")  # noqa: F821


class PayoutRun(Base):
    __tablename__ = "payout_runs"

    id:           Mapped[str]             = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    period_start: Mapped[date]            = mapped_column(Date)
    period_end:   Mapped[date]            = mapped_column(Date)
    status:       Mapped[PayoutRunStatus] = mapped_column(Enum(PayoutRunStatus, native_enum=False), default=PayoutRunStatus.DRAFT)
    total_cents:  Mapped[int]             = mapped_column(Integer, default=0)
    created_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lines: Mapped[list["PayoutLine"]] = relationship("PayoutLine", back_populates="payout_run")
