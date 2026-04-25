import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ArtistStatus(str, PyEnum):
    APPLICANT  = "applicant"
    ACTIVE     = "active"
    ON_HOLD    = "on_hold"
    DEPARTED   = "departed"


class ApplicationStatus(str, PyEnum):
    PENDING    = "pending"
    APPROVED   = "approved"
    DECLINED   = "declined"
    WAITLISTED = "waitlisted"


class Artist(Base):
    __tablename__ = "artists"

    id:           Mapped[str]  = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name:         Mapped[str]  = mapped_column(String(200))
    email:        Mapped[str]  = mapped_column(String(200), unique=True, index=True)
    phone:        Mapped[str | None] = mapped_column(String(50))
    bio:          Mapped[str | None] = mapped_column(Text)
    website:      Mapped[str | None] = mapped_column(String(500))
    instagram:    Mapped[str | None] = mapped_column(String(200))
    media_types:  Mapped[str | None] = mapped_column(String(500))
    pos_vendor_name: Mapped[str | None] = mapped_column(String(200), index=True)
    status:       Mapped[ArtistStatus] = mapped_column(Enum(ArtistStatus), default=ArtistStatus.APPLICANT)
    w9_on_file:   Mapped[bool] = mapped_column(Boolean, default=False)
    commission_rate_override: Mapped[str | None] = mapped_column(String(10))
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    portal_user:   Mapped["ArtistUser | None"]   = relationship("ArtistUser", back_populates="artist", uselist=False)
    agreements:    Mapped[list["Agreement"]]      = relationship("Agreement", back_populates="artist")
    booth_assignments: Mapped[list["BoothAssignment"]] = relationship("BoothAssignment", back_populates="artist")  # noqa: F821
    payout_lines:  Mapped[list["PayoutLine"]]     = relationship("PayoutLine", back_populates="artist")  # noqa: F821
    sale_items:    Mapped[list["SaleLineItem"]]   = relationship("SaleLineItem", back_populates="artist")  # noqa: F821


class ArtistUser(Base):
    """Portal login credentials for an artist."""
    __tablename__ = "artist_users"

    id:                   Mapped[str]           = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    artist_id:            Mapped[str]           = mapped_column(ForeignKey("artists.id"), unique=True)
    magic_link_token:     Mapped[str | None]    = mapped_column(String(200), index=True)
    magic_link_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at:        Mapped[datetime | None]  = mapped_column(DateTime(timezone=True))

    artist: Mapped["Artist"] = relationship("Artist", back_populates="portal_user")


class Agreement(Base):
    """Signed consignment/rental agreement — HTML snapshot stored at signing."""
    __tablename__ = "agreements"

    id:             Mapped[str]      = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    artist_id:      Mapped[str]      = mapped_column(ForeignKey("artists.id"), index=True)
    version:        Mapped[str]      = mapped_column(String(50))
    signed_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ip_address:     Mapped[str | None] = mapped_column(String(50))
    agreement_html: Mapped[str]      = mapped_column(Text)

    artist: Mapped["Artist"] = relationship("Artist", back_populates="agreements")


class Application(Base):
    __tablename__ = "applications"

    id:            Mapped[str]               = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name:          Mapped[str]               = mapped_column(String(200))
    email:         Mapped[str]               = mapped_column(String(200), index=True)
    phone:         Mapped[str | None]        = mapped_column(String(50))
    bio:           Mapped[str | None]        = mapped_column(Text)
    portfolio_url: Mapped[str | None]        = mapped_column(String(500))
    media_types:   Mapped[str | None]        = mapped_column(String(500))
    artist_statement: Mapped[str | None]     = mapped_column(Text)
    status:        Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.PENDING)
    submitted_at:  Mapped[datetime]          = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at:   Mapped[datetime | None]   = mapped_column(DateTime(timezone=True))
    reviewed_by:   Mapped[str | None]        = mapped_column(ForeignKey("admin_users.id"))
    notes:         Mapped[str | None]        = mapped_column(Text)
