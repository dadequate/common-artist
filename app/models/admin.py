import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AdminRole(str, PyEnum):
    OWNER   = "owner"
    MANAGER = "manager"
    STAFF   = "staff"


class AdminUser(Base):
    __tablename__ = "admin_users"

    id:            Mapped[str]       = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email:         Mapped[str]       = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str]       = mapped_column(String(200))
    role:          Mapped[AdminRole] = mapped_column(Enum(AdminRole, native_enum=False), default=AdminRole.STAFF)
    is_active:     Mapped[bool]      = mapped_column(Boolean, default=True)
    created_at:    Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
