"""Aggregate shipments into a buyer, with a deterministic credibility score and
a fact-based description (Decisions 3 & 4).

Nothing here is random or fabricated: every output is a pure function of the real
shipment signals accumulated in :class:`BuyerAggregate`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from etl_worker.domain import normalization as norm

# ── Credibility model (deterministic, documented, extensible) ──────────────────
# score = Σ weight_i * normalize_i(signal_i), clamped to [0, 1].
# Weights live in one dict so new signals can be added without touching callers.
CREDIBILITY_WEIGHTS: dict[str, float] = {
    "activity": 0.30,       # how many shipments (log-scaled, saturates ~50)
    "value": 0.30,          # total FOB USD (log-scaled, saturates ~5,000,000)
    "continuity": 0.15,     # distinct active months (linear, saturates 12)
    "supplier_diversity": 0.15,  # distinct exporter countries (log, saturates 10)
    "product_breadth": 0.10,     # distinct HS codes (log, saturates 5)
}
_ACTIVITY_K = 50.0
_VALUE_K = 5_000_000.0
_CONTINUITY_MAX = 12.0
_SUPPLIER_K = 10.0
_BREADTH_K = 5.0


def _norm_log(x: float, k: float) -> float:
    if x <= 0:
        return 0.0
    return min(math.log1p(x) / math.log1p(k), 1.0)


def _norm_lin(x: float, m: float) -> float:
    if x <= 0:
        return 0.0
    return min(x / m, 1.0)


@dataclass
class BuyerAggregate:
    """Mutable accumulator for one importer (keyed by TradeAtlas importerUrlCode)."""

    source_id: str
    clean_url: str = ""
    name: str | None = None
    country: str | None = None
    country_name: str | None = None
    shipment_count: int = 0
    total_fob_usd: float = 0.0
    total_net_weight_kg: float = 0.0
    hs_codes: set[str] = field(default_factory=set)
    exporter_countries: set[str] = field(default_factory=set)
    exporter_country_names: set[str] = field(default_factory=set)
    exporter_names: set[str] = field(default_factory=set)
    arrival_ports: set[str] = field(default_factory=set)
    active_months: set[str] = field(default_factory=set)
    product_terms: list[str] = field(default_factory=list)
    first_date: str | None = None
    last_date: str | None = None

    def add_shipment(self, raw: dict) -> None:
        if self.name is None:
            self.name = norm.clean_company_name(raw.get("importerName"))
        if self.country is None:
            self.country = norm.valid_country_code(raw.get("importerCountryCode"))
        if not self.country_name and raw.get("importerCountryName"):
            self.country_name = str(raw["importerCountryName"]).strip()
        if not self.clean_url and raw.get("importerCleanUrl"):
            self.clean_url = str(raw["importerCleanUrl"]).strip()

        self.shipment_count += 1
        self.total_fob_usd += norm.parse_money(raw.get("usdFob")) or norm.parse_money(
            raw.get("shipmentFobValue")
        )
        self.total_net_weight_kg += norm.parse_money(raw.get("netWeight"))

        for hs in norm.normalize_hs(raw.get("hsCode")):
            self.hs_codes.add(hs)

        exp_cc = norm.valid_country_code(raw.get("exporterCountryCode"))
        if exp_cc:
            self.exporter_countries.add(exp_cc)
        if raw.get("exporterCountryName"):
            self.exporter_country_names.add(str(raw["exporterCountryName"]).strip())
        exp_name = norm.clean_company_name(raw.get("exporterName"))
        if exp_name:
            self.exporter_names.add(exp_name)

        port = (raw.get("portOfArrival") or "").strip()
        if port:
            self.arrival_ports.add(port)

        ym = norm.year_month(raw.get("arrivalDate"))
        if ym:
            self.active_months.add(ym)
        arrival = (raw.get("arrivalDate") or "").strip()
        if arrival:
            self.first_date = arrival if self.first_date is None else min(self.first_date, arrival)
            self.last_date = arrival if self.last_date is None else max(self.last_date, arrival)

        term = (raw.get("productDetail") or "").strip()
        if term and len(self.product_terms) < 5 and term not in self.product_terms:
            self.product_terms.append(term[:160])

    # ── Derived outputs ──────────────────────────────────────────────────────────
    @property
    def is_valid_buyer(self) -> bool:
        """A usable buyer needs at least a real company name and a country."""
        return bool(self.name) and bool(self.country)

    def credibility(self) -> float:
        w = CREDIBILITY_WEIGHTS
        score = (
            w["activity"] * _norm_log(self.shipment_count, _ACTIVITY_K)
            + w["value"] * _norm_log(self.total_fob_usd, _VALUE_K)
            + w["continuity"] * _norm_lin(len(self.active_months), _CONTINUITY_MAX)
            + w["supplier_diversity"] * _norm_log(len(self.exporter_countries), _SUPPLIER_K)
            + w["product_breadth"] * _norm_log(len(self.hs_codes), _BREADTH_K)
        )
        return round(min(max(score, 0.0), 1.0), 3)

    def description(self) -> str:
        country = self.country_name or self.country or "an unknown market"
        suppliers = sorted(self.exporter_country_names) or sorted(self.exporter_countries)
        supplier_txt = ", ".join(suppliers[:5]) if suppliers else "various origins"
        hs_txt = ", ".join(sorted(self.hs_codes)) if self.hs_codes else "unspecified HS"
        products = "; ".join(self.product_terms[:3])
        period = (
            f" between {self.first_date} and {self.last_date}"
            if self.first_date and self.last_date
            else ""
        )
        ports = ", ".join(sorted(self.arrival_ports)[:3])
        parts = [
            f"{self.name} is an importer based in {country}, "
            f"actively sourcing goods under HS {hs_txt} from {supplier_txt}.",
            f"Observed {self.shipment_count} customs shipment(s){period}, "
            f"totalling about USD {self.total_fob_usd:,.0f} FOB "
            f"and {self.total_net_weight_kg:,.0f} kg net weight.",
        ]
        if products:
            parts.append(f"Representative products: {products}.")
        if ports:
            parts.append(f"Arrival ports: {ports}.")
        return " ".join(parts)

    def to_buyer_fields(self, provider_name: str) -> dict:
        """Map the aggregate to ``buyer`` columns + metadata (real data only)."""
        return {
            "name": self.name,
            "country": self.country,
            "hs_codes": sorted(self.hs_codes),
            "credibility_score": self.credibility(),
            "description": self.description(),
            "metadata": {
                "source": provider_name,
                "source_id": self.source_id,
                "clean_url": self.clean_url,
                "shipment_count": self.shipment_count,
                "total_usd_fob": round(self.total_fob_usd, 2),
                "total_net_weight_kg": round(self.total_net_weight_kg, 2),
                "exporter_countries": sorted(self.exporter_countries),
                "hs_codes": sorted(self.hs_codes),
                "arrival_ports": sorted(self.arrival_ports)[:10],
                "active_months": sorted(self.active_months),
                "date_range": [self.first_date, self.last_date],
                "credibility_weights": CREDIBILITY_WEIGHTS,
            },
        }
