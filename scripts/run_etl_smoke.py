"""One-shot ETL smoke runner — executes ingest tasks eagerly and prints results.

Run inside the etl-worker container (has deps + DATABASE_URL_SYNC → postgres):
    docker compose run --rm etl-worker python /run_etl_smoke.py
"""
from __future__ import annotations

import json

from etl_worker.tasks.bps_task import ingest_bps
from etl_worker.tasks.un_comtrade_task import ingest_un_comtrade


def _run(label: str, sig) -> None:
    try:
        res = sig.get()
    except Exception as exc:  # noqa: BLE001
        print(f"[{label}] ERROR: {exc}")
        return
    print(f"[{label}] {json.dumps(res, default=str)}")


def main() -> None:
    print("=== BPS ===")
    for hs in ["46", "09", "15", "03;04"]:
        _run(
            f"bps hs={hs} 2024",
            ingest_bps.apply(kwargs={"hs_code": hs, "year": 2024, "flow": "both", "frequency": "annual"}),
        )

    print("=== UN COMTRADE ===")
    for hs in ["4602", "0901"]:
        _run(
            f"comtrade hs={hs} 2023",
            ingest_un_comtrade.apply(kwargs={"hs_code": hs, "year": 2023}),
        )


if __name__ == "__main__":
    main()
