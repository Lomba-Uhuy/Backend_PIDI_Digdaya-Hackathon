"""End-to-end buyer-discovery test.

Runs inside the matching-service image (has sentence-transformers + e5-large).
Flow: login to gateway -> encode a query into a 1024-dim vector ->
POST /api/v1/matching/match-buyers -> print the ranked buyers.

    docker compose run --rm -v <host>/scripts/test_buyer_discovery.py:/t.py matching-service python /t.py
"""
from __future__ import annotations

import json
import os
import sys

import httpx
from sentence_transformers import SentenceTransformer

GATEWAY = os.environ.get("GATEWAY_URL", "http://gateway:3000")
QUERY = os.environ.get(
    "QUERY",
    "query: specialty single-origin arabica and robusta coffee green beans from Indonesia, "
    "looking for a reliable exporter, Fairtrade and organic certified",
)


def main() -> None:
    # 1) Auth
    creds = {"email": "demo@tradeconnect.id", "password": "DemoPass123!"}
    with httpx.Client(timeout=60.0) as c:
        r = c.post(f"{GATEWAY}/api/v1/auth/login", json=creds)
        if r.status_code != 200:
            r = c.post(f"{GATEWAY}/api/v1/auth/register", json={**creds, "name": "Demo"})
        token = r.json().get("accessToken")
        print(f"[auth] status={r.status_code} token_len={len(token or '')}")

        # 2) Embed the query (E5 needs the 'query:' prefix, normalized)
        print("[model] loading intfloat/multilingual-e5-large (cached after first run)...")
        model = SentenceTransformer("intfloat/multilingual-e5-large")
        vec = model.encode([QUERY], normalize_embeddings=True)[0].tolist()
        print(f"[model] embedding dims={len(vec)}")

        # 3) Buyer discovery via gateway (JWT-guarded) -> matching-service -> pgvector ANN
        body = {"embedding": vec, "top_k": 5, "category": "09"}
        mr = c.post(
            f"{GATEWAY}/api/v1/matching/match-buyers",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        print(f"[match] status={mr.status_code}")
        if mr.status_code != 200:
            print(mr.text)
            sys.exit(1)
        results = mr.json()
        print(f"[match] returned {len(results) if isinstance(results, list) else 'obj'} buyers")
        print(json.dumps(results, indent=2, default=str)[:4000])


if __name__ == "__main__":
    main()
