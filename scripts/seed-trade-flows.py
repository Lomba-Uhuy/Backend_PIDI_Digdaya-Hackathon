#!/usr/bin/env python3
"""Seed trade_flows table with realistic coffee trade data for BPS and UN Comtrade."""
from __future__ import annotations

import json
import os
from decimal import Decimal
from uuid import uuid4

try:
    from sqlalchemy import create_engine, text
except ImportError as exc:
    raise SystemExit("Install sqlalchemy: uv pip install sqlalchemy 'psycopg[binary]'") from exc

# Realistic coffee export/import unit values and total values
# Robusta Coffee: ~ $2.50 to $3.50 per kg
# Arabica Coffee: ~ $4.00 to $6.00 per kg
COFFEE_DATA = [
    # ── BPS EXPORTS (Source: BPS, Flow: X) ──
    # Germany (DEU)
    {"source": "bps", "hs_code": "090111", "partner_code": "cde", "partner_iso": "DE", "partner_name": "Jerman", "period": 2024, "val": 495000, "wt": 180000},
    {"source": "bps", "hs_code": "090121", "partner_code": "cde", "partner_iso": "DE", "partner_name": "Jerman", "period": 2024, "val": 150000, "wt": 50000},
    {"source": "bps", "hs_code": "090111", "partner_code": "cde", "partner_iso": "DE", "partner_name": "Jerman", "period": 2023, "val": 450000, "wt": 170000},
    
    # USA (USA)
    {"source": "bps", "hs_code": "090111", "partner_code": "cus", "partner_iso": "US", "partner_name": "Amerika Serikat", "period": 2024, "val": 850000, "wt": 280000},
    {"source": "bps", "hs_code": "090121", "partner_code": "cus", "partner_iso": "US", "partner_name": "Amerika Serikat", "period": 2024, "val": 220000, "wt": 70000},
    
    # Japan (JPN)
    {"source": "bps", "hs_code": "090111", "partner_code": "cjp", "partner_iso": "JP", "partner_name": "Jepang", "period": 2024, "val": 350000, "wt": 120000},
    
    # UAE (ARE)
    {"source": "bps", "hs_code": "090111", "partner_code": "cae", "partner_iso": "AE", "partner_name": "Uni Emirat Arab", "period": 2024, "val": 120000, "wt": 45000},
    
    # Singapore (SGP)
    {"source": "bps", "hs_code": "090111", "partner_code": "csg", "partner_iso": "SG", "partner_name": "Singapura", "period": 2024, "val": 95000, "wt": 32000},

    # ── UN COMTRADE IMPORTS FROM INDONESIA (Source: un_comtrade, Flow: M) ──
    # Germany (DEU, code 276)
    {"source": "un_comtrade", "hs_code": "090111", "reporter_code": "276", "reporter_iso": "DEU", "reporter_name": "Germany", "period": 2024, "val": 520000, "wt": 182000},
    {"source": "un_comtrade", "hs_code": "090121", "reporter_code": "276", "reporter_iso": "DEU", "reporter_name": "Germany", "period": 2024, "val": 155000, "wt": 51000},
    {"source": "un_comtrade", "hs_code": "090111", "reporter_code": "276", "reporter_iso": "DEU", "reporter_name": "Germany", "period": 2023, "val": 460000, "wt": 172000},
    
    # USA (USA, code 842)
    {"source": "un_comtrade", "hs_code": "090111", "reporter_code": "842", "reporter_iso": "USA", "reporter_name": "USA", "period": 2024, "val": 880000, "wt": 285000},
    {"source": "un_comtrade", "hs_code": "090121", "reporter_code": "842", "reporter_iso": "USA", "reporter_name": "USA", "period": 2024, "val": 230000, "wt": 72000},
    
    # Japan (JPN, code 392)
    {"source": "un_comtrade", "hs_code": "090111", "reporter_code": "392", "reporter_iso": "JPN", "reporter_name": "Japan", "period": 2024, "val": 360000, "wt": 122000},
    
    # UAE (ARE, code 784)
    {"source": "un_comtrade", "hs_code": "090111", "reporter_code": "784", "reporter_iso": "ARE", "reporter_name": "United Arab Emirates", "period": 2024, "val": 125000, "wt": 46000},
    
    # Singapore (SGP, code 702)
    {"source": "un_comtrade", "hs_code": "090111", "reporter_code": "702", "reporter_iso": "SGP", "reporter_name": "Singapore", "period": 2024, "val": 98000, "wt": 32500},
    
    # Netherlands (NLD, code 528)
    {"source": "un_comtrade", "hs_code": "090111", "reporter_code": "528", "reporter_iso": "NLD", "reporter_name": "Netherlands", "period": 2024, "val": 240000, "wt": 82000},
]

def seed(dsn: str) -> None:
    engine = create_engine(dsn, pool_pre_ping=True)
    print(f"Connecting to database to seed trade flows...")

    with engine.begin() as conn:
        # Clear existing seeded trade flows to avoid conflicts
        conn.execute(text("DELETE FROM trade_flows WHERE source IN ('bps', 'un_comtrade')"))
        print("Cleared existing BPS and UN Comtrade trade flows.")

        inserted = 0
        for item in COFFEE_DATA:
            flow_code = "X" if item["source"] == "bps" else "M"
            flow_name = "Export" if item["source"] == "bps" else "Import"
            
            reporter_code = "360" if item["source"] == "bps" else item.get("reporter_code")
            reporter_iso = "IDN" if item["source"] == "bps" else item.get("reporter_iso")
            reporter_name = "Indonesia" if item["source"] == "bps" else item.get("reporter_name")
            
            partner_code = item.get("partner_code") if item["source"] == "bps" else "360"
            partner_iso = item.get("partner_iso") if item["source"] == "bps" else "IDN"
            partner_name = item.get("partner_name") if item["source"] == "bps" else "Indonesia"

            conn.execute(
                text("""
                    INSERT INTO trade_flows (
                        id, source, hs_code, reporter_code, reporter_iso, reporter_name,
                        partner_code, partner_iso, partner_name,
                        partner2_code, partner2_iso, partner2_name, flow_code, flow_name,
                        customs_code, customs_name, transport_mode_code, transport_mode_name,
                        period, trade_value_usd, net_weight_kg, quantity, quantity_unit, raw_json
                    ) VALUES (
                        :id, :source, :hs_code, :rep_code, :rep_iso, :rep_name,
                        :part_code, :part_iso, :part_name,
                        '0', 'N/A', 'N/A', :flow_code, :flow_name,
                        '0', 'General customs', '0', 'N/A',
                        :period, :val, :wt, :qty, 'KG', CAST(:raw_json AS JSONB)
                    )
                """),
                {
                    "id": str(uuid4()),
                    "source": item["source"],
                    "hs_code": item["hs_code"],
                    "rep_code": reporter_code,
                    "rep_iso": reporter_iso,
                    "rep_name": reporter_name,
                    "part_code": partner_code,
                    "part_iso": partner_iso,
                    "part_name": partner_name,
                    "flow_code": flow_code,
                    "flow_name": flow_name,
                    "period": item["period"],
                    "val": Decimal(item["val"]),
                    "wt": Decimal(item["wt"]),
                    "qty": Decimal(item["wt"]),
                    "raw_json": json.dumps(item),
                }
            )
            inserted += 1

        print(f"Successfully seeded {inserted} trade flow records.")

def main() -> None:
    dsn = os.environ.get(
        "DATABASE_URL_SYNC",
        "postgresql+psycopg://tc_user:tc_pass_dev@localhost:5432/tradeconnect"
    )
    seed(dsn)

if __name__ == "__main__":
    main()
