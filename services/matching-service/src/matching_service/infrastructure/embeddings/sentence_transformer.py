"""Embedding provider — sentence-transformers singleton.

Following E5 convention:
  - 'query: ...' for the query side (product description / buyer search)
  - 'passage: ...' for the passage side (buyer profile / HS code corpus)
"""
from __future__ import annotations

import structlog

from matching_service.core.config import settings

log = structlog.get_logger(__name__)


class SentenceTransformerEmbedder:
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


_singleton: SentenceTransformerEmbedder | None = None


def get_embedder() -> SentenceTransformerEmbedder:
    global _singleton
    if _singleton is None:
        _singleton = SentenceTransformerEmbedder()
    return _singleton