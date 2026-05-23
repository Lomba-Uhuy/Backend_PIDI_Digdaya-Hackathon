"""Knowledge base retrieval — pgvector + full-text backed.

Reads from export_knowledge_base (regulations, templates, Incoterms refs,
HS code guides, INATRADE procedures, negotiation strategies, etc.)

Two retrieval strategies:
  1. search()           — vector cosine search via pgvector (requires seeded embeddings)
  2. search_by_text()   — PostgreSQL full-text search via GIN index (always works)
  3. search_smart()     — tries vector search, falls back to text search
"""
from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

# Intent → category mapping for focused retrieval
INTENT_CATEGORIES: dict[str, list[str]] = {
    "rfq":              ["incoterms", "payment_terms", "documents", "regulations"],
    "price_negotiation": ["negotiation", "incoterms", "market_intelligence"],
    "spec_inquiry":     ["documents", "regulations", "incoterms"],
    "complaint":        ["logistics", "documents", "regulations"],
    "general":          ["incoterms", "payment_terms", "negotiation", "logistics"],
}


class KnowledgeBaseRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Vector search (requires embeddings in DB) ─────────────────────────────

    async def search(self, query_embedding: list[float], top_k: int = 4) -> list[dict]:
        """pgvector cosine similarity search.

        Requires:
          • export_knowledge_base rows to have non-NULL embeddings
          • seed-knowledge-base.py run with --with-embeddings
        """
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
            rows = (
                await self._session.execute(sql, {"q": query_embedding, "k": top_k})
            ).mappings().all()
            return [dict(r) for r in rows]
        except Exception as e:  # noqa: BLE001
            log.warning("rag.kb.vector_search_failed", error=str(e))
            return []

    # ── Text search (works immediately after seeding, no embeddings needed) ──

    async def search_by_text(
        self,
        query: str,
        intent: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        """PostgreSQL full-text search with category-based pre-filter.

        Uses the GIN tsvector index created by seed-knowledge-base.py
        and the pg_trgm extension for title fuzzy matching.

        Strategy:
          1. Filter by relevant categories (based on detected intent)
          2. Rank by title fuzzy similarity (pg_trgm) + tsvector rank combined
          3. Return top_k most relevant entries
        """
        categories = INTENT_CATEGORIES.get(intent or "general", [])

        # Build two-phase SQL:
        #   Phase 1: category-scoped tsvector search
        #   Phase 2: broader title similarity as fallback
        #
        # We UNION both to ensure we always get some results even if the
        # category filter is too narrow.
        sql = text("""
            WITH category_match AS (
                SELECT
                    id, title, content, category, source,
                    ts_rank(
                        to_tsvector('english', coalesce(title,'') || ' ' || coalesce(content,'')),
                        plainto_tsquery('english', :query)
                    ) AS rank_score
                FROM export_knowledge_base
                WHERE
                    category = ANY(:cats)
                    AND to_tsvector('english', coalesce(title,'') || ' ' || coalesce(content,''))
                        @@ plainto_tsquery('english', :query)
                ORDER BY rank_score DESC
                LIMIT :k
            ),
            title_fuzzy AS (
                SELECT
                    id, title, content, category, source,
                    similarity(title, :query)::float AS rank_score
                FROM export_knowledge_base
                WHERE
                    similarity(title, :query) > 0.05
                ORDER BY rank_score DESC
                LIMIT :k
            ),
            fallback AS (
                -- Last resort: return entries from relevant categories ordered by created_at
                SELECT
                    id, title, content, category, source,
                    0.01 AS rank_score
                FROM export_knowledge_base
                WHERE category = ANY(:cats)
                ORDER BY created_at DESC
                LIMIT :k
            )
            SELECT DISTINCT ON (id) id, title, content, category, source, rank_score
            FROM (
                SELECT * FROM category_match
                UNION ALL
                SELECT * FROM title_fuzzy
                UNION ALL
                SELECT * FROM fallback
            ) combined
            ORDER BY id, rank_score DESC
            LIMIT :k
        """)

        try:
            rows = (
                await self._session.execute(
                    sql,
                    {"query": query, "cats": categories, "k": top_k},
                )
            ).mappings().all()
            result = [dict(r) for r in rows]
            log.debug(
                "rag.kb.text_search",
                intent=intent,
                categories=categories,
                results=len(result),
            )
            return result
        except Exception as e:  # noqa: BLE001
            log.warning("rag.kb.text_search_failed", error=str(e))
            # Ultra-simple fallback: just return rows from relevant categories
            return await self._simple_category_fallback(categories, top_k)

    async def _simple_category_fallback(
        self, categories: list[str], top_k: int
    ) -> list[dict]:
        """Absolute fallback: return any KB entries from relevant categories."""
        try:
            sql = text("""
                SELECT id, title, content, category, source
                FROM export_knowledge_base
                WHERE category = ANY(:cats)
                ORDER BY created_at DESC
                LIMIT :k
            """)
            rows = (
                await self._session.execute(sql, {"cats": categories, "k": top_k})
            ).mappings().all()
            return [dict(r) for r in rows]
        except Exception:  # noqa: BLE001
            return []

    # ── Smart retrieval (vector → text fallback) ──────────────────────────────

    async def search_smart(
        self,
        query: str,
        query_embedding: list[float] | None,
        intent: str | None = None,
        top_k: int = 4,
    ) -> list[dict]:
        """Try vector search; fall back to text search if no results or no embedding."""
        if query_embedding:
            results = await self.search(query_embedding, top_k=top_k)
            if results:
                log.debug("rag.kb.strategy", strategy="vector", results=len(results))
                return results

        results = await self.search_by_text(query, intent=intent, top_k=top_k)
        log.debug("rag.kb.strategy", strategy="text", results=len(results))
        return results

    # ── Formatting helper ─────────────────────────────────────────────────────

    @staticmethod
    def format_context(entries: list[dict]) -> str:
        """Format KB entries as a readable context block for the LLM prompt."""
        if not entries:
            return (
                "Catatan: Basis pengetahuan ekspor belum diisi. "
                "Berikan respons berdasarkan praktik terbaik ekspor umum."
            )
        parts: list[str] = []
        for i, entry in enumerate(entries, 1):
            category = entry.get("category", "general")
            title = entry.get("title", "")
            content = entry.get("content", "")
            source = entry.get("source", "")
            source_note = f" [Source: {source}]" if source else ""
            parts.append(
                f"[{i}] [{category.upper()}]{source_note}\n"
                f"## {title}\n"
                f"{content}\n"
            )
        return "\n---\n".join(parts)
