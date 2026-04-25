import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Booth(Base):
    __tablename__ = "booths"

    id:                Mapped[str]       = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name:              Mapped[str]       = mapped_column(String(100), unique=True)
    tier:              Mapped[str]       = mapped_column(String(50))
    monthly_rate_cents: Mapped[int]      = mapped_column(Integer)
    notes:             Mapped[str | None] = mapped_column(Text)
    is_active:         Mapped[bool]      = mapped_column(Boolean, default=True)

    assignments: Mapped[list["BoothAssignment"]] = relationship("BoothAssignment", back_populates="booth")


class BoothAssignment(Base):
    __tablename__ = "booth_assignments"

    id:         Mapped[str]        = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booth_id:   Mapped[str]        = mapped_column(ForeignKey("booths.id"), index=True)
    artist_id:  Mapped[str]        = mapped_column(ForeignKey("artists.id"), index=True)
    started_at: Mapped[date]       = mapped_column(Date)
    ended_at:   Mapped[date | None] = mapped_column(Date)

    booth:  Mapped["Booth"]   = relationship("Booth",  back_populates="assignments")
    artist: Mapped["Artist"]  = relationship("Artist", back_populates="booth_assignments")  # noqa: F821


class RentCharge(Base):
    __tablename__ = "rent_charges"

    id:           Mapped[str]      = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    artist_id:    Mapped[str]      = mapped_column(ForeignKey("artists.id"), index=True)
    booth_id:     Mapped[str]      = mapped_column(ForeignKey("booths.id"))
    period_start: Mapped[date]     = mapped_column(Date)
    period_end:   Mapped[date]     = mapped_column(Date)
    amount_cents: Mapped[int]      = mapped_column(Integer)
    paid_cents:   Mapped[int]      = mapped_column(Integer, default=0)
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def balance_cents(self) -> int:
        return self.amount_cents - self.paid_cents

    @property
    def is_overdue(self) -> bool:
        from datetime import date as today_mod
        return self.balance_cents > 0 and self.period_end < today_mod.today()
