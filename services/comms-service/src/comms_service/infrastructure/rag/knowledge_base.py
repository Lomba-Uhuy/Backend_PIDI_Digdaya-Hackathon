"""Knowledge base retrieval — pgvector backed.

Reads from export_knowledge_base (regulations, templates, Incoterms refs,
HS code guides, INATRADE procedures, etc.)
"""
from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


class KnowledgeBaseRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(self, query_embedding: list[float], top_k: int = 4) -> list[dict]:
        sql = text(
            """
            SELECT id, title, content, category, source,
                   (embedding <=> :q) AS distance
            FROM export_knowledge_base
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :q
            LIMIT :k
            """
        )
        try:
            rows = (await self._session.execute(sql, {"q": query_embedding, "k": top_k})).mappings().all()
            return [dict(r) for r in rows]
        except Exception as e:  # noqa: BLE001
            log.warning("rag.kb.search_failed", error=str(e))
            return []