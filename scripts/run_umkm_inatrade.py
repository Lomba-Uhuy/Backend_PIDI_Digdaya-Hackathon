"""Populate umkm.inatrade_data from ingested trade_flows for each UMKM."""
from __future__ import annotations

import json

from sqlalchemy import text

from etl_worker.db.session import get_session_factory
from etl_worker.tasks.inatrade_task import update_umkm_inatrade_data


def main() -> None:
    sf = get_session_factory()
    with sf() as s:
        umkm_ids = [str(r[0]) for r in s.execute(text("SELECT id FROM umkm")).fetchall()]
    print(f"umkm rows: {len(umkm_ids)}")
    for uid in umkm_ids:
        # demo UMKM are coffee producers (product hs 090111) → chapter 0901
        res = update_umkm_inatrade_data.apply(kwargs={"umkm_id": uid, "hs_code": "0901", "year": 2024}).get()
        print(json.dumps(res, default=str))


if __name__ == "__main__":
    main()
