"""Thin pgvector ANN facade — cosine distance via <=> operator."""
from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


class PgVectorStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search_buyers(self, query_embedding: list[float], top_k: int = 10) -> list[dict]:
        sql = text(
            """
            SELECT b.id, b.name, b.country, b.credibility_score, b.is_synthetic,
                   (be.embedding <=> :q) AS distance
            FROM buyer_embedding be
            JOIN buyer b ON b.id = be.buyer_id
            WHERE b.is_active = TRUE
            ORDER BY be.embedding <=> :q
            LIMIT :k
            """
        )
        rows = (await self._session.execute(sql, {"q": query_embedding, "k": top_k})).mappings().all()
        return [dict(r) for r in rows]