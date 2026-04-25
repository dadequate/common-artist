import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Sale(Base):
    """A POS order — groups one or more SaleLineItems."""
    __tablename__ = "sales"

    id:          Mapped[str]      = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_id: Mapped[str]      = mapped_column(String(200), unique=True, index=True)
    source:      Mapped[str]      = mapped_column(String(50))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    line_items: Mapped[list["SaleLineItem"]] = relationship("SaleLineItem", back_populates="sale")


class SaleLineItem(Base):
    """One artist's portion of a sale. Commission calculated at import time."""
    __tablename__ = "sale_line_items"

    id:                   Mapped[str]       = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sale_id:              Mapped[str | None] = mapped_column(ForeignKey("sales.id"), index=True)
    external_id:          Mapped[str]       = mapped_column(String(200), unique=True, index=True)
    order_external_id:    Mapped[str]       = mapped_column(String(200), index=True)
    artist_id:            Mapped[str | None] = mapped_column(ForeignKey("artists.id"), index=True)
    artist_external_id:   Mapped[str]       = mapped_column(String(200), index=True)
    amount_cents:         Mapped[int]       = mapped_column(Integer)
    commission_rate:      Mapped[float]     = mapped_column(Numeric(5, 4))
    commission_cents:     Mapped[int]       = mapped_column(Integer)
    source:               Mapped[str]       = mapped_column(String(50))
    raw:                  Mapped[dict]      = mapped_column(JSON)
    occurred_at:          Mapped[datetime]  = mapped_column(DateTime(timezone=True), index=True)
    payout_line_id:       Mapped[str | None] = mapped_column(ForeignKey("payout_lines.id"), index=True)
    created_at:           Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())

    sale:   Mapped["Sale | None"]        = relationship("Sale", back_populates="line_items")
    artist: Mapped["Artist | None"]      = relationship("Artist", back_populates="sale_items")  # noqa: F821
    payout_line: Mapped["PayoutLine | None"] = relationship("PayoutLine", back_populates="sale_items")  # noqa: F821

    @property
    def net_cents(self) -> int:
        return self.amount_cents - self.commission_cents
