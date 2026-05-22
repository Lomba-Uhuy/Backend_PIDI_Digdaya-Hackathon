"""Buyer ORM — managed by matching-service (ETL writes via worker)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from matching_service.infrastructure.db.base import Base


class BuyerORM(Base):
    __tablename__ = "buyer"

    id:                 Mapped[UUID]     = mapped_column(primary_key=True, default=uuid4)
    name:               Mapped[str]      = mapped_column(String(255), nullable=False)
    country:            Mapped[str]      = mapped_column(String(2), index=True, nullable=False)
    hs_codes:           Mapped[list[str]] = mapped_column(ARRAY(String(10)), default=list, nullable=False)
    credibility_score:  Mapped[float]    = mapped_column(Numeric(4, 3), default=0.0, index=True, nullable=False)
    min_order_qty:      Mapped[int]      = mapped_column(Integer, default=1, nullable=False)
    description:        Mapped[str | None] = mapped_column(nullable=True)
    is_active:          Mapped[bool]     = mapped_column(Boolean, default=True, nullable=False)
    is_synthetic:       Mapped[bool]     = mapped_column(Boolean, default=False, nullable=False)
    metadata_json:      Mapped[dict]     = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at:         Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at:         Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)