"""Provider dependency-injection factory.

Business logic asks for a ``BuyerSourceProvider`` by config; concrete providers
register here. Adding a provider = add a builder to ``_REGISTRY`` (Decision 7).
"""
from __future__ import annotations

from collections.abc import Callable

from etl_worker.config import Settings, settings as default_settings
from etl_worker.providers.base import BuyerSourceProvider, ProviderError
from etl_worker.providers.tradeatlas import TradeAtlasProvider

_REGISTRY: dict[str, Callable[[Settings], BuyerSourceProvider]] = {
    "tradeatlas": TradeAtlasProvider,
}


def get_buyer_source_provider(settings: Settings | None = None) -> BuyerSourceProvider:
    cfg = settings or default_settings
    key = (cfg.buyer_source_provider or "").strip().lower()
    builder = _REGISTRY.get(key)
    if builder is None:
        raise ProviderError(
            f"Unknown buyer_source_provider '{cfg.buyer_source_provider}'. "
            f"Available: {', '.join(sorted(_REGISTRY))}"
        )
    return builder(cfg)
