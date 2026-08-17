from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ModelProfile(Base):
    __tablename__ = "model_profile"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    technical_config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    medical_options_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    exposed_to_medical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class KnowledgeProfile(Base):
    __tablename__ = "knowledge_profile"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    technical_config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    medical_options_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    exposed_to_medical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
