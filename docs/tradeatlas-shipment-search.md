# TradeAtlas — `shipment-search` API Reconnaissance (hackathon data source)

> ⚠️ **Status:** internal/authenticated endpoint of a 3rd-party product, reverse-engineered
> for a **competition/demo** only. Auth is via the user's **login session cookie**. This is
> **not** a public API and using it in production would violate TradeAtlas ToS + their
> customs-data licensing. Treat as a **demo-only** buyer source; keep the session cookie in
> an env var, never hardcode, rotate after the event.

## Endpoint
| | |
|---|---|
| **URL** | `https://app.tradeatlas.com/api/search/unified` |
| **Method** | `POST` |
| **Content-Type** | `application/json` |
| **Auth** | Cookie `tradeatlas2_session` (Laravel encrypted session). Also sends `langCode`, `colorPref` (cosmetic). |
| **CORS** | `access-control-allow-credentials: true`, origin locked to `https://app.tradeatlas.com` → requests must be **server-side** (send `Origin`/`Referer: https://app.tradeatlas.com`). |
| **Behind** | Cloudflare (may throttle/challenge on volume). |

### Required headers (server-side)
```
content-type: application/json
accept: application/json, text/plain, */*
origin: https://app.tradeatlas.com
referer: https://app.tradeatlas.com/en/shipment-search
user-agent: <a real browser UA>
cookie: tradeatlas2_session=<SESSION>; langCode=en
```

## Request payload
```jsonc
{
  "searchParameters": {
    "startDate": "2022-01-01T00:00:00.000Z",   // ISO 8601, inclusive
    "endDate":   "2022-12-31T00:00:00.000Z",   // ISO 8601, inclusive
    "hsCodes": [                                 // filter by product (repeatable)
      { "text": "090111", "value": "090111", "ops": [] }
    ],
    "importerFirmNames": [],   // filter by specific buyer companies
    "exporterFirmNames": [],   // filter by specific supplier companies
    "brandNames": [],
    "productDetails": [],      // free-text product keywords
    "arrivalPortNames": [],
    "departurePortNames": [],
    "importerCountries": [     // BUYER country (this is what we want)
      { "text": "United States", "value": "united-states", "ops": [], "isGroup": false }
    ],
    "exporterCountries": [],   // SUPPLIER country
    "firmTypes": ["0"],        // firm type toggle (observed "0")
    "page": 1                  // 1-based pagination
  },
  "filterBy": [                // post-search refine (arrays empty = no refine)
    { "key": "hsCode",            "value": [] },
    { "key": "importerFirmType",  "value": ["none"] },
    { "key": "exporterFirmType",  "value": ["none"] },
    { "key": "importer",          "value": [] },
    { "key": "exporter",          "value": [] }
  ],
  "orderBy": {},                        // empty = default (by arrivalDate desc)
  "searchScope": "shipments_search"     // scope selector
}
```

### Parameter reference
| Field | Type | Meaning |
|---|---|---|
| `searchParameters.startDate/endDate` | ISO datetime | Date window (arrival date). |
| `searchParameters.hsCodes[]` | `{text,value,ops}` | Product HS filter. `value` = HS string (2/4/6+ digits, e.g. `090111`). |
| `searchParameters.importerCountries[]` | `{text,value,ops,isGroup}` | **Buyer** country. `value` = slug (e.g. `united-states`). `isGroup` for regional groups. |
| `searchParameters.exporterCountries[]` | same | Supplier country. |
| `searchParameters.importerFirmNames[] / exporterFirmNames[]` | string[] | Restrict to named firms. |
| `searchParameters.brandNames[] / productDetails[] / arrivalPortNames[] / departurePortNames[]` | string[] | Extra filters. |
| `searchParameters.firmTypes[]` | string[] | Firm-type filter (observed `"0"`). |
| `searchParameters.page` | int | 1-based page. |
| `filterBy[]` | `{key,value[]}` | Server-side refine on results. |
| `orderBy` | object | Sort spec (empty = default). |
| `searchScope` | string | `"shipments_search"` (row-per-shipment). Other scopes likely exist for importer/exporter aggregation. |

**UI ↔ query-string mapping** (from the page URL): `dates=<start>,<end>`, `hs=<internalId>:<hsCode>`, `icnty=<importerCountry>`, `firms=<0|1>`.

## Response
```jsonc
{
  "result": {
    "page": 1,
    "perPage": 30,               // fixed page size
    "totalPageCount": 1198,
    "maxDownloadSize": 10000,    // hard cap on bulk export
    "totalShipmentCount": 35923, // total matches (great for market sizing)
    "shipments": [ /* row objects */ ]
  }
}
```

### `shipments[]` fields (complete)
| Field | Notes / use |
|---|---|
| `importerUrlCode` | **Stable unique id** for the importer (use for dedup). |
| `importerCleanUrl` | Slug for the company profile page. |
| `importerName` | **Buyer company name** → `buyer.name`. |
| `importerCountryCode` / `importerCountryName` | **Buyer country** (ISO-2) → `buyer.country`. |
| `exporterUrlCode` / `exporterCleanUrl` / `exporterName` | Supplier (the competitor side). |
| `exporterCountryCode` / `exporterCountryName` | Supplier country. |
| `arrivalDate` | Shipment date (YYYY-MM-DD). |
| `hsCode` | HS code (varies 6–12 digits, sometimes `a|b|c`). Normalize to first 6. |
| `hsCodeDescription` | HS text (often empty). |
| `productDetail` | Free-text goods description (rich; good for embeddings). |
| `quantity` / `quantityUnit` | e.g. `640` / `Bag`, or kg. Units inconsistent. |
| `netWeight` / `netWeightUnit`, `grossWeight` / `grossWeightUnit` | Weights (kg). |
| `shipmentFobValue`, `usdFob`, `shipmentCifValue`, `usdCif`, `statisticalValueUsd` | Trade values (USD; many `0.00`). |
| `unitPrice`, `fobCurrency`, `cifCurrency`, `freightAmount`, `insuranceAmount` | Pricing/finance (often empty). |
| `portOfArrival` / `portOfDeparture` | Ports. |
| `totalTeus`, `containerCount`, `packageAmount`, `packagesUnit` | Volume/logistics. |
| `transportCompany`, `transportType`, `vesselName` | Carrier/vessel. |
| `billOfLadingNo`, `declarationNumber`, `regime`, `incoterms`, `paymentType` | Customs/trade doc fields. |
| `manufacturingCompany`, `notifyParty`, `notifyAddress`, `brandName`, `itemNo` | Misc. |

**Data-quality notes (real caveats):** many numeric fields are `"0.00"`/empty; `importerName` sometimes `N/A`/`INTERNATIONAL`/`ACCOUNTS PAYABLE`; `hsCode` length varies. Any wrapper must **clean/aggregate**, not trust single rows.

## Pagination
- `perPage = 30`, loop `page = 1..totalPageCount` (cap for demo, respect `maxDownloadSize = 10000`).
- `totalShipmentCount` is itself a **market-sizing** signal (how many shipments of HS X to country Y).

## Mapping → our `buyer` table (real records, `is_synthetic = FALSE`)
Group `shipments[]` **by `importerUrlCode`** (one buyer per importer), then:
| `buyer` column | Source |
|---|---|
| `name` | `importerName` (skip junk: `N/A`, `INTERNATIONAL`, `ACCOUNTS PAYABLE`, `TO THE ORDER…`). |
| `country` | `importerCountryCode`. |
| `hs_codes` | distinct `hsCode[:6]` across their shipments. |
| `min_order_qty` | **left default** (units inconsistent → cannot derive cleanly; do NOT fabricate). |
| `credibility_score` | **derived, transparent** from real signals (shipment_count + total USD FOB), normalized 0–1, documented — NOT invented. Alternatively left 0 if you prefer. |
| `description` | built from real aggregates (countries sourced from, top products, shipment count, total value) → feeds embedding. |
| `metadata` | `{ "source":"tradeatlas", "source_id": importerUrlCode, "clean_url": importerCleanUrl, "shipment_count", "total_usd_fob", "exporter_countries":[...], "ports":[...], "hs_codes":[...], "date_range":[start,end] }`. |
| `is_synthetic` | `FALSE` (real customs-derived company). |

**Idempotency / dedup:** upsert keyed on `metadata->>'source_id'` (= `importerUrlCode`).

## Also available (not captured yet)
- A **per-company profile** endpoint almost certainly exists (keyed by `importerUrlCode` / `importerCleanUrl`, e.g. the `/en/importer/<cleanUrl>` page). If you want richer buyer profiles (address, full history), capture that request too.

---

# Implemented sync pipeline (etl-worker)

Real buyers are synchronised into the `buyer` table by the ETL worker. Synthetic
buyers (`is_synthetic = TRUE`) are preserved and coexist with real ones.

**Modules**
- `providers/base.py` — `BuyerSourceProvider` interface + `ShipmentQuery`/`ProviderPage` + errors.
- `providers/tradeatlas.py` — `TradeAtlasProvider` (httpx + tenacity retry/backoff, timeout, auth handling, pagination).
- `providers/factory.py` — DI registry (`get_buyer_source_provider`).
- `domain/normalization.py` — deterministic cleaning (junk names, HS, country, money, month).
- `domain/buyer_intelligence.py` — `BuyerAggregate` + credibility + description.
- `db/buyer_sync_repo.py` — idempotent upsert (dedup by `metadata.source_id`) + sync-run checkpoints.
- `tasks/tradeatlas_buyer_sync_task.py` — Celery task `etl.sync_tradeatlas_buyers`.

**Credibility score** (deterministic, extensible — weights in `CREDIBILITY_WEIGHTS`):
```
score = 0.30·log(shipments,50) + 0.30·log(totalFOB,5e6) + 0.15·lin(activeMonths,12)
      + 0.15·log(exporterCountries,10) + 0.10·log(hsCodes,5)     # clamped [0,1]
```
where `log(x,k)=ln(1+x)/ln(1+k)`, `lin(x,m)=min(x/m,1)`. Pure function of real signals.

**DB changes** — `infra/db/migrations/20260719_tradeatlas_buyer_sync.sql` (also in `init.sql`):
unique index `uq_buyer_source_identity` on `(metadata.source, metadata.source_id)`,
`idx_buyer_source`, and table `buyer_sync_run` (status/checkpoint/history).

**Env** (see `.env.example`): `TRADEATLAS_SESSION_COOKIE` (secret, full Cookie header),
`TRADEATLAS_*`, `BUYER_SOURCE_PROVIDER`, `BUYER_SYNC_BATCH_SIZE`.

**Trigger (dynamic HS + markets — nothing hardcoded):**
```python
celery_app.send_task("etl.sync_tradeatlas_buyers", kwargs={
    "hs_codes": ["090111"],                 # from product RAG/classification
    "importer_countries": ["United States"],# from user target markets
    "start_date": "2022-01-01", "end_date": "2022-12-31",
})
```
Returns `{status, run_id, shipments_seen, buyers_upserted, buyers_skipped, embedding_tasks_dispatched}`.
`status="auth_required"` when the session cookie is missing/expired (no data fabricated).

**Idempotency / resume:** upserts are keyed on `source_id` with full overwrite, so
re-running the same params safely repairs an interrupted run; `buyer_sync_run` records
the page checkpoint + outcome. After upsert, `embeddings.generate_buyer` is dispatched
so real buyers become matchable via the existing `POST /matching/search`.

**Apply migration to an existing DB:**
```
docker compose exec -T postgres psql -U tc_user -d tradeconnect \
  < infra/db/migrations/20260719_tradeatlas_buyer_sync.sql
```

## Frontend-facing API (gateway → matching-service, JWT-guarded)
The frontend **never** talks to TradeAtlas; every response comes from the synced DB.

| Gateway route | Upstream | Purpose |
|---|---|---|
| `POST /api/v1/matching/buyers/sync` | `POST /api/v1/buyers/sync` | **Trigger** a real-buyer sync. Body `{hs_codes[], importer_countries[], exporter_countries[], start_date, end_date, max_pages}` (dynamic — HS from product RAG, markets from user). Enqueues `etl.sync_tradeatlas_buyers`, returns `{status, task_id}`. |
| `GET /api/v1/matching/buyers` | `GET /api/v1/buyers` | Search/list. Query: `q, country[], hs, source, is_synthetic, min_credibility, sort_by, sort_dir, page, per_page`. Returns `{items, page, per_page, total, total_pages}`; each item exposes `is_synthetic` + `source`. |
| `GET /api/v1/matching/buyers/stats` | `GET /api/v1/buyers/stats` | `{total, real, synthetic, by_source[], top_countries[]}`. |
| `GET /api/v1/matching/buyers/:id` | `GET /api/v1/buyers/{id}` | Full buyer detail incl. `description` + source `metadata`. |

Real buyers also flow through the existing `POST /api/v1/matching/search` (semantic match)
once embedded, so the current buyer-discovery/dashboard match UI picks them up automatically.
