import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SyncCursor(Base):
    """Tracks last successful sync time per POS provider."""
    __tablename__ = "sync_cursors"

    id:             Mapped[str]           = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider:       Mapped[str]           = mapped_column(String(50), unique=True, index=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error:     Mapped[str | None]    = mapped_column(Text)
    updated_at:     Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ErrorLog(Base):
    """Monitor error table — every unhandled exception lands here."""
    __tablename__ = "error_logs"

    id:         Mapped[str]      = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event:      Mapped[str]      = mapped_column(String(200), index=True)
    message:    Mapped[str]      = mapped_column(Text)
    details:    Mapped[dict | None] = mapped_column(JSON)
    resolved:   Mapped[bool]     = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
