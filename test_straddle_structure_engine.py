import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from straddle_structure_engine import (
    StraddleStructureEngine,
)


def create_schema(connection):
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

        CREATE TABLE strike_straddle_minute_bars (
            timestamp TEXT,
            trading_date TEXT,
            index_symbol TEXT,
            index_name TEXT,
            expiry_date TEXT,
            spot_price REAL,
            atm_strike INTEGER,
            strike INTEGER,
            relative_steps INTEGER,
            ce_symbol TEXT,
            pe_symbol TEXT,
            ce_ltp REAL,
            pe_ltp REAL,
            straddle REAL,
            session_open REAL,
            previous_close REAL,
            change_1m REAL,
            change_1m_pct REAL,
            change_from_open REAL,
            change_from_open_pct REAL,
            overnight_change REAL,
            overnight_change_pct REAL,
            combined_oi INTEGER,
            combined_volume INTEGER
        );

        CREATE TABLE reference_locks (
            trading_date TEXT,
            reference_type TEXT,
            lock_time TEXT,
            index_symbol TEXT,
            expiry_date TEXT,
            atm_strike INTEGER,
            spot_price REAL,
            atm_ce REAL,
            atm_pe REAL,
            straddle REAL,
            payload_json TEXT
        );
        """
    )


def insert_session(
    connection,
    prices,
):
    for minute, price in enumerate(
        prices,
        start=15,
    ):
        timestamp = (
            f"2026-07-27T09:{minute:02d}:00+05:30"
        )

        connection.execute(
            """
            INSERT INTO strike_straddle_minute_bars
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                timestamp,
                "2026-07-27",
                "NSE:NIFTY50-INDEX",
                "NIFTY",
                "2026-07-28",
                25000,
                25000,
                25000,
                0,
                "CE",
                "PE",
                price / 2,
                price / 2,
                price,
                prices[0],
                prices[0],
                0,
                0,
                0,
                0,
                0,
                0,
                10000,
                1000 + minute * 100,
            ),
        )

    latest_timestamp = (
        f"2026-07-27T09:"
        f"{14 + len(prices):02d}:00+05:30"
    )

    connection.execute(
        """
        INSERT INTO intelligence_summaries
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            latest_timestamp,
            "2026-07-27",
            "NSE:NIFTY50-INDEX",
            "2026-07-28",
            25000,
            25000,
            prices[-1],
            0,
            0,
            0,
            0,
            0,
            100,
            0,
            0,
            "TEST",
            "TEST",
            "TEST",
        ),
    )

    connection.execute(
        """
        INSERT INTO reference_locks
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            "2026-07-27",
            "BATTLE_0921",
            "09:21",
            "NSE:NIFTY50-INDEX",
            "2026-07-28",
            25000,
            25000,
            125,
            125,
            250,
            "{}",
        ),
    )


with TemporaryDirectory() as tmp:
    db_path = Path(tmp) / "expansion.db"
    connection = sqlite3.connect(db_path)
    create_schema(connection)

    prices = [
        250, 249, 251, 252, 253,
        254, 255, 256, 257, 258,
        259, 260, 261, 262, 263,
        270, 278, 286,
    ]

    insert_session(
        connection,
        prices,
    )

    connection.commit()
    connection.close()

    with StraddleStructureEngine(
        db_path
    ) as engine:
        report = engine.analyse(
            "NSE:NIFTY50-INDEX",
            "2026-07-28",
        )

        assert (
            report.opening_range_ready
            is True
        )
        assert report.above_orh is True
        assert report.above_vwap is True
        assert (
            report.above_ema75_high
            is True
        )
        assert (
            report.structure_state
            == "EXPANSION_BREAKOUT"
        )
        assert (
            report.straddle_bias
            == "LONG_STRADDLE"
        )
        assert (
            report.short_straddle_stance
            == "AVOID"
        )


with TemporaryDirectory() as tmp:
    db_path = Path(tmp) / "decay.db"
    connection = sqlite3.connect(db_path)
    create_schema(connection)

    prices = [
        250, 249, 251, 252, 253,
        254, 255, 256, 257, 258,
        259, 260, 261, 262, 263,
        240, 225, 210,
    ]

    insert_session(
        connection,
        prices,
    )

    connection.commit()
    connection.close()

    with StraddleStructureEngine(
        db_path
    ) as engine:
        report = engine.analyse(
            "NSE:NIFTY50-INDEX",
            "2026-07-28",
        )

        assert report.below_orl is True
        assert (
            report.structure_state
            == "DECAY_BREAKDOWN"
        )
        assert (
            report.straddle_bias
            == "SHORT_STRADDLE"
        )
        assert (
            report.short_straddle_stance
            == "FAVOURABLE"
        )


print(
    "ALL STRADDLE STRUCTURE ENGINE V1 "
    "TESTS PASSED"
)
