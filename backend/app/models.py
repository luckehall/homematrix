import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum, Integer
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
    totp_secret: Mapped[str]  = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool]          = mapped_column(Boolean, default=False)
    require_2fa: Mapped[bool]     = mapped_column(Boolean, default=False, server_default="false")
    google_auth: Mapped[bool]     = mapped_column(Boolean, default=False, server_default="false")
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

import json

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]           = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str]    = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]= mapped_column(DateTime, default=datetime.utcnow)
    require_2fa: Mapped[bool]     = mapped_column(Boolean, default=False, server_default="false")

    permissions: Mapped[list["RolePermission"]] = relationship(back_populates="role", cascade="all, delete")
    users: Mapped[list["UserRole"]] = relationship(back_populates="role", cascade="all, delete")

class UserRole(Base):
    __tablename__ = "user_roles"

    id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    created_at: Mapped[datetime]= mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship()
    role: Mapped["Role"] = relationship(back_populates="users")

class RolePermission(Base):
    __tablename__ = "role_permissions"

    id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    host_id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("ha_hosts.id"), nullable=False)
    # Domini consentiti: JSON array es. ["switch","light","sensor"] — null = tutti
    allowed_domains: Mapped[str]= mapped_column(Text, nullable=True)
    # Entità specifiche: JSON array es. ["switch.luce_sala"] — null = tutte
    allowed_entities: Mapped[str]= mapped_column(Text, nullable=True)

    role: Mapped["Role"] = relationship(back_populates="permissions")
    host: Mapped["HAHost"] = relationship()

class TrustedDevice(Base):
    __tablename__ = "trusted_devices"

    id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    device_token: Mapped[str]   = mapped_column(String(128), unique=True, nullable=False)
    device_name: Mapped[str]    = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime]= mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime]= mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship()

class CustomView(Base):
    __tablename__ = "custom_views"

    id: Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    host_id: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("ha_hosts.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str]           = mapped_column(String(200), nullable=False)
    slug: Mapped[str]            = mapped_column(String(200), unique=True, nullable=False)
    order: Mapped[int]           = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    widgets: Mapped[list["ViewWidget"]] = relationship(back_populates="view", cascade="all, delete", order_by="ViewWidget.order")

class ViewWidget(Base):
    __tablename__ = "view_widgets"

    id: Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    view_id: Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), ForeignKey("custom_views.id", ondelete="CASCADE"), nullable=False)
    entity_id: Mapped[str]       = mapped_column(String(200), nullable=False)
    label: Mapped[str]           = mapped_column(String(200), nullable=True)
    icon: Mapped[str]            = mapped_column(String(50), nullable=True)
    color: Mapped[str]           = mapped_column(String(50), nullable=True)
    size: Mapped[str]            = mapped_column(String(20), default="medium")  # small, medium, large
    order: Mapped[int]           = mapped_column(Integer, default=0)

    view: Mapped["CustomView"] = relationship(back_populates="widgets")
