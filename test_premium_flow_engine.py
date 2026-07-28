import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from premium_flow_engine import (
    PremiumFlowEngine,
)


with TemporaryDirectory() as tmp:
    db_path = Path(tmp) / "test.db"

    connection = sqlite3.connect(db_path)

    connection.executescript(
        """
        CREATE TABLE intelligence_summaries (
            timestamp TEXT,
            trading_date TEXT,
            index_symbol TEXT,
            expiry_date TEXT,
            spot_price REAL,
            atm_strike INTEGER,
            atm_straddle REAL,
            change_1m_pct REAL,
            change_from_open_pct REAL,
            overnight_change_pct REAL,
            change_vs_0921_pct REAL,
            change_vs_0925_pct REAL,
            premium_remaining_pct REAL,
            rotation_count INTEGER,
            net_shift_points INTEGER,
            decay_state TEXT,
            rotation_state TEXT,
            commander_state TEXT
        );

        CREATE TABLE option_minute_bars (
            timestamp TEXT,
            trading_date TEXT,
            index_symbol TEXT,
            index_name TEXT,
            expiry_date TEXT,
            spot_price REAL,
            atm_strike INTEGER,
            ladder_label TEXT,
            option_symbol TEXT,
            strike INTEGER,
            option_type TEXT,
            ltp REAL,
            change_value REAL,
            change_pct REAL,
            previous_close REAL,
            bid REAL,
            ask REAL,
            spread REAL,
            volume INTEGER,
            oi INTEGER,
            iv REAL,
            delta REAL,
            gamma REAL,
            theta REAL,
            vega REAL
        );
        """
    )

    connection.execute(
        """
        INSERT INTO intelligence_summaries
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            "2026-07-27T09:22:00+05:30",
            "2026-07-27",
            "NSE:NIFTY50-INDEX",
            "2026-07-28",
            25110,
            25100,
            240,
            -1,
            -4,
            -3,
            -2,
            0,
            96,
            1,
            100,
            "SLOW_DECAY",
            "UPWARD_ROTATION",
            "MIXED",
        ),
    )

    previous_rows = [
        ("ATM_CE", "ATMCE", 25100, "CE", 130),
        ("OTM1_CE", "OTM1CE", 25200, "CE", 82),
        ("OTM2_CE", "OTM2CE", 25300, "CE", 50),
        ("ATM_PE", "ATMPE", 25100, "PE", 120),
        ("OTM1_PE", "OTM1PE", 25000, "PE", 78),
        ("OTM2_PE", "OTM2PE", 24900, "PE", 48),
    ]

    current_rows = [
        ("ATM_CE", "ATMCE", 25100, "CE", 118, 3000, 15000),
        ("OTM1_CE", "OTM1CE", 25200, "CE", 96, 9000, 22000),
        ("OTM2_CE", "OTM2CE", 25300, "CE", 66, 12000, 28000),
        ("ATM_PE", "ATMPE", 25100, "PE", 116, 2500, 14000),
        ("OTM1_PE", "OTM1PE", 25000, "PE", 76, 2000, 12000),
        ("OTM2_PE", "OTM2PE", 24900, "PE", 46, 1500, 9000),
    ]

    for label, symbol, strike, option_type, ltp in previous_rows:
        connection.execute(
            """
            INSERT INTO option_minute_bars
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "2026-07-27T09:21:00+05:30",
                "2026-07-27",
                "NSE:NIFTY50-INDEX",
                "NIFTY",
                "2026-07-28",
                25090,
                25100,
                label,
                symbol,
                strike,
                option_type,
                ltp,
                0,
                0,
                ltp,
                ltp - 0.5,
                ltp + 0.5,
                1,
                1000,
                5000,
                14,
                0,
                0,
                0,
                0,
            ),
        )

    for label, symbol, strike, option_type, ltp, volume, oi in current_rows:
        connection.execute(
            """
            INSERT INTO option_minute_bars
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "2026-07-27T09:22:00+05:30",
                "2026-07-27",
                "NSE:NIFTY50-INDEX",
                "NIFTY",
                "2026-07-28",
                25110,
                25100,
                label,
                symbol,
                strike,
                option_type,
                ltp,
                0,
                0,
                ltp,
                ltp - 0.5,
                ltp + 0.5,
                1,
                volume,
                oi,
                14,
                0,
                0,
                0,
                0,
            ),
        )

    connection.commit()
    connection.close()

    with PremiumFlowEngine(db_path) as engine:
        report = engine.analyse(
            "NSE:NIFTY50-INDEX",
            "2026-07-28",
        )

        assert report.call_leader_strike == 25300
        assert report.call_leader_display == "OTM2 CALL — 25300 CE"
        assert report.dominant_side == "CALL"
        assert "25300 CE" in report.atm_erosion_destination

print("ALL PREMIUM FLOW ENGINE V1 TESTS PASSED")
