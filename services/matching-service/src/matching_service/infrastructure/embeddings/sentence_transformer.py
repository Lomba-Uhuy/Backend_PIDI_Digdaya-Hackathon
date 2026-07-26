"""Embedding provider — factory + sentence-transformers fallback.

The get_embedder() factory returns either:
  - GeminiEmbedder  (when EMBEDDING_PROVIDER=gemini)  — cloud API, no torch needed
  - SentenceTransformerEmbedder (when EMBEDDING_PROVIDER=local) — local model, heavy

Default is "gemini" for cloud-native, lightweight operation.
"""
from __future__ import annotations

from typing import Protocol

import structlog

from matching_service.core.config import settings

log = structlog.get_logger(__name__)


class Embedder(Protocol):
    """Common interface for all embedding providers."""
    model_name: str

    def embed_sync(self, texts: list[str]) -> list[list[float]]: ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    """Local sentence-transformers model (heavy — requires torch + model download)."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model
        self._model = None  # lazy

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer

        log.info("embedder.loading", model=self.model_name)
        self._model = SentenceTransformer(self.model_name, token=settings.hf_token)
        log.info("embedder.loaded")

    def embed_sync(self, texts: list[str]) -> list[list[float]]:
        self._ensure_loaded()
        assert self._model is not None
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [vec.tolist() for vec in vectors]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return self.embed_sync(texts)


_singleton: Embedder | None = None


def get_embedder() -> Embedder:
    """Factory: returns the configured embedding provider (Gemini or local)."""
    global _singleton
    if _singleton is None:
        if settings.embedding_provider == "gemini":
            from matching_service.infrastructure.embeddings.gemini_embedder import GeminiEmbedder
            log.info("embedder.factory", provider="gemini", model=settings.embedding_model)
            _singleton = GeminiEmbedder()  # type: ignore[assignment]
        else:
            log.info("embedder.factory", provider="local", model=settings.embedding_model)
            _singleton = SentenceTransformerEmbedder()  # type: ignore[assignment]
    return _singleton