"""HS Code classification via multilingual sentence-transformers.

Model: intfloat/multilingual-e5-large
- Supports Indonesian + English in one model
- 1024-dim embeddings
- Requires 'query:' / 'passage:' prefix per E5 family convention
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import structlog

log = structlog.get_logger(__name__)

# Demo corpus. In production, ingest WCO HS database (~5K codes) via ETL.
HS_CORPUS: dict[str, str] = {
    "4602": "basketwork, wickerwork and other articles made from plaiting materials; loofah, coconut shell, rattan, bamboo",
    "0901": "coffee, whether or not roasted or decaffeinated; coffee husks and skins; coffee substitutes",
    "0902": "tea, whether or not flavoured; green tea, black tea, oolong tea",
    "1404": "vegetable products not elsewhere specified or included; coconut fiber, coir, natural plant materials",
    "9403": "other furniture and parts thereof; wooden furniture, bamboo furniture, rattan furniture",
    "3305": "preparations for use on the hair; hair shampoos, hair conditioners, natural hair care",
    "2106": "food preparations not elsewhere specified; processed food, packaged food, snack food",
    "6302": "bed linen, table linen, toilet linen and kitchen linen; batik, traditional woven fabric",
    "1513": "coconut, palm kernel or babassu oil and their fractions",
    "0801": "coconuts, brazil nuts and cashew nuts, fresh or dried, whether or not shelled or peeled",
    "1801": "cocoa beans, whole or broken, raw or roasted",
}


@dataclass
class HSCodeResult:
    hs_code: str
    description: str
    confidence: float
    top_k: list[dict]


class HSCodeClassifierService:
    """Multilingual semantic classifier — singleton, lazy-loaded."""

    MODEL_NAME = "intfloat/multilingual-e5-large"

    def __init__(self) -> None:
        self._model = None  # lazy
        self._corpus_embeddings: np.ndarray | None = None
        self._corpus_keys: list[str] = list(HS_CORPUS.keys())

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        # Local import — sentence-transformers is heavy
        from sentence_transformers import SentenceTransformer

        log.info("hs_classifier.model.loading", model=self.MODEL_NAME)
        self._model = SentenceTransformer(self.MODEL_NAME)
        corpus_texts = [f"passage: {desc}" for desc in HS_CORPUS.values()]
        self._corpus_embeddings = self._model.encode(  # type: ignore[union-attr]
            corpus_texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
        log.info("hs_classifier.corpus.precomputed", size=len(HS_CORPUS))

    def classify(self, product_description: str, top_k: int = 3) -> HSCodeResult:
        self._ensure_loaded()
        assert self._model is not None and self._corpus_embeddings is not None

        query_text = f"query: {product_description}"
        query_embedding = self._model.encode(query_text, normalize_embeddings=True)

        # Cosine similarity (since both sides are normalized -> dot product)
        similarities = np.dot(self._corpus_embeddings, query_embedding)
        ranked = np.argsort(similarities)[::-1]

        candidates = []
        for idx in ranked[:top_k]:
            code = self._corpus_keys[idx]
            candidates.append({
                "hs_code": code,
                "description": HS_CORPUS[code],
                "confidence": float(similarities[idx]),
            })

        best = candidates[0]
        log.info(
            "hs_classifier.classified",
            preview=product_description[:60],
            hs_code=best["hs_code"],
            confidence=best["confidence"],
        )
        return HSCodeResult(
            hs_code=best["hs_code"],
            description=best["description"],
            confidence=best["confidence"],
            top_k=candidates,
        )


_singleton: HSCodeClassifierService | None = None


def get_hs_classifier() -> HSCodeClassifierService:
    global _singleton
    if _singleton is None:
        _singleton = HSCodeClassifierService()
    return _singleton