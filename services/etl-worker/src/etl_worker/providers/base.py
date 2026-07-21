"""BuyerSourceProvider — abstraction over external importer/shipment data sources.

Business logic (aggregation, scoring, upsert) depends only on this interface, so
new providers can be plugged in without touching the sync pipeline (Decision 7).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date


# ── Errors ────────────────────────────────────────────────────────────────────
class ProviderError(RuntimeError):
    """Generic, retryable provider failure (network / 5xx / malformed)."""


class ProviderAuthError(ProviderError):
    """Auth/session failure (expired cookie, 401/403, Cloudflare block).

    NON-retryable: the operator must supply a fresh credential. The sync job
    stops cleanly and records this so it can resume once the credential is set.
    """


class ProviderRateLimitError(ProviderError):
    """Upstream rate limiting (HTTP 429) — retryable with backoff."""


# ── Query / result models ─────────────────────────────────────────────────────
@dataclass(frozen=True)
class ShipmentQuery:
    """A shipment search, fully derived from dynamic inputs (HS + markets).

    No HS code or country is hardcoded — callers pass what the product-intelligence
    pipeline / user target markets produce (Decisions 5 & 6).
    """

    hs_codes: list[str]
    importer_countries: list[str] = field(default_factory=list)
    exporter_countries: list[str] = field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None
    page: int = 1

    def with_page(self, page: int) -> "ShipmentQuery":
        return ShipmentQuery(
            hs_codes=self.hs_codes,
            importer_countries=self.importer_countries,
            exporter_countries=self.exporter_countries,
            start_date=self.start_date,
            end_date=self.end_date,
            page=page,
        )


@dataclass(frozen=True)
class ProviderPage:
    """One page of raw shipment rows plus pagination metadata."""

    page: int
    per_page: int
    total_pages: int
    total_count: int
    shipments: list[dict]


class BuyerSourceProvider(ABC):
    """Contract every buyer-data source must implement."""

    #: short, stable identifier persisted on each buyer (``metadata.source``)
    name: str = "base"

    @abstractmethod
    def fetch_page(self, query: ShipmentQuery) -> ProviderPage:
        """Fetch a single page. Must raise ``ProviderAuthError`` on auth failure."""
        raise NotImplementedError

    def iter_pages(self, query: ShipmentQuery, max_pages: int) -> Iterator[ProviderPage]:
        """Iterate pages 1..N with N = min(total_pages, max_pages).

        Pagination lives here (Decision 8) so providers only implement one page.
        """
        first = self.fetch_page(query.with_page(1))
        yield first
        last_page = min(first.total_pages, max_pages) if max_pages > 0 else first.total_pages
        for page in range(2, last_page + 1):
            yield self.fetch_page(query.with_page(page))
