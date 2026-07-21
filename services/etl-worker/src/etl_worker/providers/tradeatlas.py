"""TradeAtlas Unified Search adapter.

Wraps ``POST /api/search/unified`` (documented in docs/tradeatlas-shipment-search.md).
Auth is the operator's login session cookie, injected from config (never hardcoded).
CORS on the endpoint requires same-origin ``Origin``/``Referer`` headers.
"""
from __future__ import annotations

import structlog
from curl_cffi import requests as cffi
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from etl_worker.config import Settings
from etl_worker.providers.base import (
    BuyerSourceProvider,
    ProviderAuthError,
    ProviderError,
    ProviderPage,
    ProviderRateLimitError,
    ShipmentQuery,
)

log = structlog.get_logger(__name__)


def _country_slug(value: str) -> str:
    """UI uses lowercase-hyphen slugs (e.g. 'United States' -> 'united-states')."""
    return value.strip().lower().replace(" ", "-")


class TradeAtlasProvider(BuyerSourceProvider):
    name = "tradeatlas"

    def __init__(self, settings: Settings) -> None:
        if not settings.tradeatlas_session_cookie:
            raise ProviderAuthError(
                "TRADEATLAS_SESSION_COOKIE is not configured — cannot authenticate."
            )
        self._settings = settings
        self._url = settings.tradeatlas_base_url.rstrip("/") + settings.tradeatlas_search_path
        self._origin = settings.tradeatlas_base_url.rstrip("/")
        # Mimic the real browser request as closely as possible so Cloudflare's
        # header/bot checks are more likely to pass. (A managed JS/TLS challenge
        # can still block a server-side client — handled as ProviderAuthError.)
        self._headers = {
            "content-type": "application/json",
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "origin": self._origin,
            "referer": f"{self._origin}/en/shipment-search",
            "user-agent": settings.tradeatlas_user_agent,
            "dnt": "1",
            "priority": "u=1, i",
            "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Microsoft Edge";v="150"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "cookie": settings.tradeatlas_session_cookie,
        }

    # ── Payload ────────────────────────────────────────────────────────────────
    def _build_payload(self, q: ShipmentQuery) -> dict:
        start = (q.start_date.isoformat() if q.start_date else "1970-01-01") + "T00:00:00.000Z"
        end = (q.end_date.isoformat() if q.end_date else "2100-01-01") + "T00:00:00.000Z"
        return {
            "searchParameters": {
                "startDate": start,
                "endDate": end,
                "hsCodes": [{"text": hs, "value": hs, "ops": []} for hs in q.hs_codes],
                "importerFirmNames": [],
                "exporterFirmNames": [],
                "brandNames": [],
                "productDetails": [],
                "arrivalPortNames": [],
                "departurePortNames": [],
                "importerCountries": [
                    {"text": c, "value": _country_slug(c), "ops": [], "isGroup": False}
                    for c in q.importer_countries
                ],
                "exporterCountries": [
                    {"text": c, "value": _country_slug(c), "ops": [], "isGroup": False}
                    for c in q.exporter_countries
                ],
                "firmTypes": ["0"],
                "page": q.page,
            },
            "filterBy": [
                {"key": "hsCode", "value": []},
                {"key": "importerFirmType", "value": ["none"]},
                {"key": "exporterFirmType", "value": ["none"]},
                {"key": "importer", "value": []},
                {"key": "exporter", "value": []},
            ],
            "orderBy": {},
            "searchScope": "shipments_search",
        }

    # ── Fetch (retry/backoff/timeout) ────────────────────────────────────────────
    @retry(
        retry=retry_if_exception_type(ProviderRateLimitError),
        wait=wait_exponential_jitter(initial=1.0, max=30.0),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def fetch_page(self, query: ShipmentQuery) -> ProviderPage:
        payload = self._build_payload(query)
        try:
            # curl_cffi impersonates a real browser's TLS/JA3 + HTTP2 fingerprint
            # so Cloudflare treats us like the browser (with the same session cookie).
            resp = cffi.post(
                self._url,
                json=payload,
                headers=self._headers,
                timeout=self._settings.tradeatlas_timeout_seconds,
                impersonate=self._settings.tradeatlas_impersonate,
            )
        except Exception as exc:  # noqa: BLE001 — curl_cffi transport/timeout/TLS errors
            log.warning("tradeatlas.network_error", page=query.page, error=str(exc))
            raise ProviderRateLimitError(f"TradeAtlas request failed: {exc}") from exc

        if resp.status_code in (401, 403):
            # Expired session or Cloudflare challenge — non-retryable auth failure.
            snippet = (resp.text or "")[:200].replace("\n", " ")
            is_cf = "cloudflare" in snippet.lower() or "just a moment" in snippet.lower()
            raise ProviderAuthError(
                f"TradeAtlas auth failed (HTTP {resp.status_code}; "
                f"{'Cloudflare challenge' if is_cf else 'app/session'}); "
                f"refresh the session cookie. body[:200]={snippet!r}"
            )
        if resp.status_code == 429:
            raise ProviderRateLimitError("TradeAtlas rate limit (HTTP 429)")
        if resp.status_code >= 500:
            raise ProviderRateLimitError(f"TradeAtlas upstream error (HTTP {resp.status_code})")
        if resp.status_code != 200:
            raise ProviderError(f"TradeAtlas unexpected status {resp.status_code}")

        try:
            body = resp.json()
        except ValueError as exc:
            raise ProviderError(f"TradeAtlas response was not JSON: {exc}") from exc

        result = body.get("result")
        if not isinstance(result, dict):
            raise ProviderError("TradeAtlas response missing 'result' object")

        shipments = result.get("shipments") or []
        if not isinstance(shipments, list):
            raise ProviderError("TradeAtlas 'result.shipments' is not a list")

        return ProviderPage(
            page=int(result.get("page") or query.page),
            per_page=int(result.get("perPage") or self._settings.tradeatlas_page_size),
            total_pages=int(result.get("totalPageCount") or 0),
            total_count=int(result.get("totalShipmentCount") or 0),
            shipments=shipments,
        )
