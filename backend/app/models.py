import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db import Base
import enum

class UserStatus(str, enum.Enum):
    pending  = "pending"
    active   = "active"
    revoked  = "revoked"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str]          = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str]      = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str]= mapped_column(String(255), nullable=False)
    status: Mapped[UserStatus]  = mapped_column(Enum(UserStatus), default=UserStatus.pending)
    is_admin: Mapped[bool]      = mapped_column(Boolean, default=False)
    request_reason: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]= mapped_column(DateTime, default=datetime.utcnow)
    approved_at: Mapped[datetime]= mapped_column(DateTime, nullable=True)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete")

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    refresh_token: Mapped[str]   = mapped_column(String(512), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    revoked: Mapped[bool]        = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="sessions")

class HAHost(Base):
    __tablename__ = "ha_hosts"

    id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]          = mapped_column(String(255), nullable=False)
    base_url: Mapped[str]      = mapped_column(String(512), nullable=False)
    token: Mapped[str]         = mapped_column(Text, nullable=False)
    description: Mapped[str]   = mapped_column(Text, nullable=True)
    active: Mapped[bool]       = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]= mapped_column(DateTime, default=datetime.utcnow)
