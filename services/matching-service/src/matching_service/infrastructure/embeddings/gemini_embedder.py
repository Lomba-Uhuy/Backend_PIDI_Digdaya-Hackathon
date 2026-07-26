"""Embedding provider — Google Gemini API.

Uses the google-genai SDK to generate embeddings via Gemini Embedding 2.
Supports Matryoshka Representation Learning (MRL) for flexible output
dimensions, so we can match the existing vector(1024) schema.

Drop-in replacement for SentenceTransformerEmbedder.
"""
from __future__ import annotations

import asyncio
from typing import Any

import structlog

from matching_service.core.config import settings

log = structlog.get_logger(__name__)


class GeminiEmbedder:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model
        self._dimensions = settings.embedding_dimensions
        self._client: Any | None = None  # lazy

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        from google import genai

        log.info("embedder.gemini.init", model=self.model_name, dimensions=self._dimensions)
        self._client = genai.Client(api_key=settings.gemini_api_key)
        log.info("embedder.gemini.ready")

    def embed_sync(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings synchronously via Gemini API."""
        self._ensure_client()
        assert self._client is not None

        results: list[list[float]] = []
        # Batch in groups of 100 (Gemini limit per request)
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            result = self._client.models.embed_content(
                model=self.model_name,
                contents=batch,
                config={"output_dimensionality": self._dimensions},
            )
            for emb in result.embeddings:
                results.append(list(emb.values))

        return results

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Async wrapper — runs Gemini API call in executor to avoid blocking."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_sync, texts)


_singleton: GeminiEmbedder | None = None


def get_gemini_embedder() -> GeminiEmbedder:
    global _singleton
    if _singleton is None:
        _singleton = GeminiEmbedder()
    return _singleton
