"""pgvector embedding tables."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from matching_service.core.config import settings
from matching_service.infrastructure.db.base import Base

DIM = settings.embedding_dimensions


class BuyerEmbedding(Base):
    __tablename__ = "buyer_embedding"

    id:         Mapped[UUID]    = mapped_column(primary_key=True, default=uuid4)
    buyer_id:   Mapped[UUID]    = mapped_column(ForeignKey("buyer.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    model:      Mapped[str]     = mapped_column(String(64), nullable=False)
    embedding:  Mapped[list[float]] = mapped_column(Vector(DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ProductEmbedding(Base):
    __tablename__ = "product_embedding"

    id:          Mapped[UUID]    = mapped_column(primary_key=True, default=uuid4)
    product_id:  Mapped[UUID]    = mapped_column(unique=True, index=True, nullable=False)
    model:       Mapped[str]     = mapped_column(String(64), nullable=False)
    embedding:   Mapped[list[float]] = mapped_column(Vector(DIM), nullable=False)
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)