"""
OPERATION COMMANDER
Module  : Premium Intelligence Database — 1 Minute Recorder
Mission : Record. Remember. Explain. Never Predict.

SOURCE OF TRUTH
---------------
Raw premium observations are stored every 1 minute.

Derived views
-------------
1m  -> execution / acceleration / sudden premium shift
5m  -> structure / VWAP / EMA / consolidation
15m -> conviction / sustained expansion / decay regime

Raw Greeks are stored but must not be printed on the live terminal.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


DEFAULT_DB_PATH = "premium_intelligence_1m.db"
RAW_RESOLUTION = "1"

LADDER_LABELS = (
    "ITM3_CE",
    "ITM2_CE",
    "ITM1_CE",
    "ATM_CE",
    "OTM1_CE",
    "OTM2_CE",
    "OTM3_CE",
    "ITM3_PE",
    "ITM2_PE",
    "ITM1_PE",
    "ATM_PE",
    "OTM1_PE",
    "OTM2_PE",
    "OTM3_PE",
)

VISIBLE_TERMINAL_OUTPUTS = (
    "PREMIUM_BEHAVIOUR",
    "STRADDLE_BEHAVIOUR",
    "ATM_ROTATION",
    "DECAY_STATUS",
    "REMAINING_DECAY",
    "GAMMA_PRESSURE",
    "TIME_PASS_INDEX",
)

DATABASE_ONLY_FIELDS = (
    "delta",
    "gamma",
    "theta",
    "vega",
    "iv",
)


@dataclass(frozen=True)
class OptionMinuteBar:
    timestamp: str
    trading_date: str
    index_symbol: str
    index_name: str
    expiry_date: str
    spot_price: float
    atm_strike: int
    ladder_label: str
    option_symbol: str
    strike: int
    option_type: str
    open: float
    high: float
    low: float
    close: float
    ltp: float
    bid: float
    ask: float
    spread: float
    volume: int
    oi: int
    iv: float
    delta: float
    gamma: float
    theta: float
    vega: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StraddleMinuteBar:
    timestamp: str
    trading_date: str
    index_symbol: str
    index_name: str
    expiry_date: str
    spot_price: float
    atm_strike: int
    ce_symbol: str
    pe_symbol: str
    ce_close: float
    pe_close: float
    straddle_close: float
    change_1m: float
    change_1m_pct: float
    atm_shift: int
    reference_type: str = "LIVE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def pct_change(current: float, previous: float) -> float:
    if previous <= 0:
        return 0.0
    return ((current - previous) / previous) * 100.0


class PremiumIntelligence1M:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def __enter__(self) -> "PremiumIntelligence1M":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS option_minute_bars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                index_symbol TEXT NOT NULL,
                index_name TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                spot_price REAL NOT NULL,
                atm_strike INTEGER NOT NULL,
                ladder_label TEXT NOT NULL,
                option_symbol TEXT NOT NULL,
                strike INTEGER NOT NULL,
                option_type TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                ltp REAL NOT NULL,
                bid REAL NOT NULL,
                ask REAL NOT NULL,
                spread REAL NOT NULL,
                volume INTEGER NOT NULL,
                oi INTEGER NOT NULL,
                iv REAL NOT NULL,
                delta REAL NOT NULL,
                gamma REAL NOT NULL,
                theta REAL NOT NULL,
                vega REAL NOT NULL,
                UNIQUE(timestamp, option_symbol)
            );

            CREATE INDEX IF NOT EXISTS idx_option_minute_lookup
            ON option_minute_bars (
                index_symbol,
                expiry_date,
                ladder_label,
                timestamp
            );

            CREATE INDEX IF NOT EXISTS idx_option_symbol_time
            ON option_minute_bars (
                option_symbol,
                timestamp
            );

            CREATE TABLE IF NOT EXISTS straddle_minute_bars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                index_symbol TEXT NOT NULL,
                index_name TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                spot_price REAL NOT NULL,
                atm_strike INTEGER NOT NULL,
                ce_symbol TEXT NOT NULL,
                pe_symbol TEXT NOT NULL,
                ce_close REAL NOT NULL,
                pe_close REAL NOT NULL,
                straddle_close REAL NOT NULL,
                change_1m REAL NOT NULL,
                change_1m_pct REAL NOT NULL,
                atm_shift INTEGER NOT NULL,
                reference_type TEXT NOT NULL,
                UNIQUE(timestamp, index_symbol, expiry_date, atm_strike)
            );

            CREATE INDEX IF NOT EXISTS idx_straddle_minute_lookup
            ON straddle_minute_bars (
                index_symbol,
                expiry_date,
                timestamp
            );

            CREATE TABLE IF NOT EXISTS strike_rotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                index_symbol TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                old_atm_strike INTEGER NOT NULL,
                new_atm_strike INTEGER NOT NULL,
                spot_price REAL NOT NULL,
                shift_points INTEGER NOT NULL,
                direction TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_rotation_lookup
            ON strike_rotations (
                index_symbol,
                expiry_date,
                timestamp
            );

            CREATE TABLE IF NOT EXISTS reference_locks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trading_date TEXT NOT NULL,
                lock_time TEXT NOT NULL,
                reference_type TEXT NOT NULL,
                index_symbol TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                atm_strike INTEGER NOT NULL,
                spot_price REAL NOT NULL,
                atm_ce_close REAL NOT NULL,
                atm_pe_close REAL NOT NULL,
                straddle_close REAL NOT NULL,
                payload_json TEXT NOT NULL,
                UNIQUE(
                    trading_date,
                    reference_type,
                    index_symbol,
                    expiry_date
                )
            );
            """
        )
        self.connection.commit()

    def latest_straddle(
        self,
        *,
        index_symbol: str,
        expiry_date: str,
    ) -> Optional[Dict[str, Any]]:
        row = self.connection.execute(
            """
            SELECT *
            FROM straddle_minute_bars
            WHERE index_symbol = ?
              AND expiry_date = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (index_symbol, expiry_date),
        ).fetchone()

        return dict(row) if row else None

    def insert_option_bars(
        self,
        bars: Sequence[OptionMinuteBar],
    ) -> int:
        if not bars:
            return 0

        self.connection.executemany(
            """
            INSERT OR REPLACE INTO option_minute_bars (
                timestamp, trading_date, index_symbol, index_name,
                expiry_date, spot_price, atm_strike, ladder_label,
                option_symbol, strike, option_type, open, high, low,
                close, ltp, bid, ask, spread, volume, oi,
                iv, delta, gamma, theta, vega
            ) VALUES (
                :timestamp, :trading_date, :index_symbol, :index_name,
                :expiry_date, :spot_price, :atm_strike, :ladder_label,
                :option_symbol, :strike, :option_type, :open, :high, :low,
                :close, :ltp, :bid, :ask, :spread, :volume, :oi,
                :iv, :delta, :gamma, :theta, :vega
            )
            """,
            [bar.to_dict() for bar in bars],
        )
        self.connection.commit()
        return len(bars)

    def insert_straddle_bar(
        self,
        bar: StraddleMinuteBar,
    ) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO straddle_minute_bars (
                timestamp, trading_date, index_symbol, index_name,
                expiry_date, spot_price, atm_strike, ce_symbol,
                pe_symbol, ce_close, pe_close, straddle_close,
                change_1m, change_1m_pct, atm_shift, reference_type
            ) VALUES (
                :timestamp, :trading_date, :index_symbol, :index_name,
                :expiry_date, :spot_price, :atm_strike, :ce_symbol,
                :pe_symbol, :ce_close, :pe_close, :straddle_close,
                :change_1m, :change_1m_pct, :atm_shift, :reference_type
            )
            """,
            bar.to_dict(),
        )
        self.connection.commit()

    def insert_rotation(
        self,
        *,
        timestamp: str,
        trading_date: str,
        index_symbol: str,
        expiry_date: str,
        old_atm: int,
        new_atm: int,
        spot_price: float,
    ) -> None:
        shift = new_atm - old_atm

        self.connection.execute(
            """
            INSERT INTO strike_rotations (
                timestamp, trading_date, index_symbol, expiry_date,
                old_atm_strike, new_atm_strike, spot_price,
                shift_points, direction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                trading_date,
                index_symbol,
                expiry_date,
                old_atm,
                new_atm,
                spot_price,
                shift,
                "UP" if shift > 0 else "DOWN",
            ),
        )
        self.connection.commit()

    def save_reference_lock(
        self,
        *,
        trading_date: str,
        lock_time: str,
        reference_type: str,
        index_symbol: str,
        expiry_date: str,
        atm_strike: int,
        spot_price: float,
        atm_ce_close: float,
        atm_pe_close: float,
        payload: Mapping[str, Any],
    ) -> None:
        self.connection.execute(
            """
            INSERT OR REPLACE INTO reference_locks (
                trading_date, lock_time, reference_type,
                index_symbol, expiry_date, atm_strike,
                spot_price, atm_ce_close, atm_pe_close,
                straddle_close, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trading_date,
                lock_time,
                reference_type,
                index_symbol,
                expiry_date,
                atm_strike,
                spot_price,
                atm_ce_close,
                atm_pe_close,
                atm_ce_close + atm_pe_close,
                json.dumps(dict(payload), default=str),
            ),
        )
        self.connection.commit()

    def fetch_option_history(
        self,
        *,
        index_symbol: str,
        expiry_date: str,
        ladder_label: str,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM option_minute_bars
            WHERE index_symbol = ?
              AND expiry_date = ?
              AND ladder_label = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (
                index_symbol,
                expiry_date,
                ladder_label,
                limit,
            ),
        ).fetchall()

        return [dict(row) for row in reversed(rows)]

    def fetch_straddle_history(
        self,
        *,
        index_symbol: str,
        expiry_date: str,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM straddle_minute_bars
            WHERE index_symbol = ?
              AND expiry_date = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (
                index_symbol,
                expiry_date,
                limit,
            ),
        ).fetchall()

        return [dict(row) for row in reversed(rows)]

    def database_stats(self) -> Dict[str, int]:
        stats = {}

        for table in (
            "option_minute_bars",
            "straddle_minute_bars",
            "strike_rotations",
            "reference_locks",
        ):
            row = self.connection.execute(
                f"SELECT COUNT(*) AS count FROM {table}"
            ).fetchone()

            stats[table] = int(row["count"])

        return stats


def build_option_bar(
    *,
    timestamp: str,
    trading_date: str,
    index_symbol: str,
    index_name: str,
    expiry_date: str,
    spot_price: float,
    atm_strike: int,
    ladder_label: str,
    contract: Mapping[str, Any],
) -> OptionMinuteBar:
    close = safe_float(
        contract.get("close")
        or contract.get("ltp")
    )
    bid = safe_float(contract.get("bid"))
    ask = safe_float(contract.get("ask"))

    return OptionMinuteBar(
        timestamp=timestamp,
        trading_date=trading_date,
        index_symbol=index_symbol,
        index_name=index_name,
        expiry_date=expiry_date,
        spot_price=spot_price,
        atm_strike=atm_strike,
        ladder_label=ladder_label,
        option_symbol=str(
            contract.get("symbol")
            or contract.get("option_symbol")
            or f"{index_symbol}:{ladder_label}"
        ),
        strike=safe_int(contract.get("strike")),
        option_type=str(
            contract.get("option_type")
            or ""
        ).upper(),
        open=safe_float(contract.get("open"), close),
        high=safe_float(contract.get("high"), close),
        low=safe_float(contract.get("low"), close),
        close=close,
        ltp=safe_float(contract.get("ltp"), close),
        bid=bid,
        ask=ask,
        spread=round(max(ask - bid, 0.0), 4),
        volume=safe_int(contract.get("volume")),
        oi=safe_int(contract.get("oi")),
        iv=safe_float(contract.get("iv")),
        delta=safe_float(contract.get("delta")),
        gamma=safe_float(contract.get("gamma")),
        theta=safe_float(contract.get("theta")),
        vega=safe_float(contract.get("vega")),
    )


def record_one_minute_snapshot(
    database: PremiumIntelligence1M,
    snapshot: Mapping[str, Any],
    *,
    index_symbol: str,
    timestamp: Optional[str] = None,
    reference_type: str = "LIVE",
) -> Dict[str, Any]:
    timestamp = timestamp or now_utc_iso()
    trading_date = timestamp[:10]

    index_name = str(
        snapshot.get("index_name")
        or index_symbol
    )
    expiry_date = str(
        snapshot.get("expiry_date")
        or "UNKNOWN"
    )
    spot_price = safe_float(
        snapshot.get("spot_price")
    )
    atm_strike = safe_int(
        snapshot.get("atm_strike")
    )
    contracts = snapshot.get("contracts") or {}

    previous_straddle = database.latest_straddle(
        index_symbol=index_symbol,
        expiry_date=expiry_date,
    )

    option_bars: List[OptionMinuteBar] = []
    missing_labels: List[str] = []

    for ladder_label in LADDER_LABELS:
        contract = contracts.get(ladder_label)

        if not contract:
            missing_labels.append(ladder_label)
            continue

        option_bars.append(
            build_option_bar(
                timestamp=timestamp,
                trading_date=trading_date,
                index_symbol=index_symbol,
                index_name=index_name,
                expiry_date=expiry_date,
                spot_price=spot_price,
                atm_strike=atm_strike,
                ladder_label=ladder_label,
                contract=contract,
            )
        )

    inserted = database.insert_option_bars(
        option_bars
    )

    atm_ce = next(
        (
            item
            for item in option_bars
            if item.ladder_label == "ATM_CE"
        ),
        None,
    )
    atm_pe = next(
        (
            item
            for item in option_bars
            if item.ladder_label == "ATM_PE"
        ),
        None,
    )

    straddle_recorded = False
    rotation_recorded = False
    straddle_close = 0.0

    if atm_ce and atm_pe:
        straddle_close = atm_ce.close + atm_pe.close

        previous_close = (
            safe_float(
                previous_straddle.get("straddle_close")
            )
            if previous_straddle
            else straddle_close
        )

        previous_atm = (
            safe_int(
                previous_straddle.get("atm_strike")
            )
            if previous_straddle
            else atm_strike
        )

        atm_shift = atm_strike - previous_atm

        database.insert_straddle_bar(
            StraddleMinuteBar(
                timestamp=timestamp,
                trading_date=trading_date,
                index_symbol=index_symbol,
                index_name=index_name,
                expiry_date=expiry_date,
                spot_price=spot_price,
                atm_strike=atm_strike,
                ce_symbol=atm_ce.option_symbol,
                pe_symbol=atm_pe.option_symbol,
                ce_close=atm_ce.close,
                pe_close=atm_pe.close,
                straddle_close=straddle_close,
                change_1m=round(
                    straddle_close - previous_close,
                    4,
                ),
                change_1m_pct=round(
                    pct_change(
                        straddle_close,
                        previous_close,
                    ),
                    4,
                ),
                atm_shift=atm_shift,
                reference_type=reference_type,
            )
        )

        straddle_recorded = True

        if atm_shift != 0:
            database.insert_rotation(
                timestamp=timestamp,
                trading_date=trading_date,
                index_symbol=index_symbol,
                expiry_date=expiry_date,
                old_atm=previous_atm,
                new_atm=atm_strike,
                spot_price=spot_price,
            )
            rotation_recorded = True

    return {
        "status": "RECORDED",
        "resolution": RAW_RESOLUTION,
        "timestamp": timestamp,
        "index_symbol": index_symbol,
        "expiry_date": expiry_date,
        "atm_strike": atm_strike,
        "contracts_inserted": inserted,
        "missing_labels": missing_labels,
        "straddle_recorded": straddle_recorded,
        "straddle_close": round(
            straddle_close,
            2,
        ),
        "rotation_recorded": rotation_recorded,
    }


def aggregate_minute_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    bucket_minutes: int,
) -> List[Dict[str, Any]]:
    """
    Pure-Python resampler for stored 1-minute option rows.
    Produces OHLCV-style buckets for 5m / 15m analysis.
    """
    if bucket_minutes <= 0:
        raise ValueError(
            "bucket_minutes must be greater than zero"
        )

    buckets: Dict[str, List[Mapping[str, Any]]] = {}

    for row in rows:
        timestamp = datetime.fromisoformat(
            str(row["timestamp"])
        )

        minute = (
            timestamp.minute // bucket_minutes
        ) * bucket_minutes

        bucket_time = timestamp.replace(
            minute=minute,
            second=0,
            microsecond=0,
        ).isoformat()

        buckets.setdefault(
            bucket_time,
            [],
        ).append(row)

    output = []

    for bucket_time in sorted(buckets):
        items = buckets[bucket_time]

        output.append(
            {
                "timestamp": bucket_time,
                "open": safe_float(items[0].get("open")),
                "high": max(
                    safe_float(item.get("high"))
                    for item in items
                ),
                "low": min(
                    safe_float(item.get("low"))
                    for item in items
                ),
                "close": safe_float(
                    items[-1].get("close")
                ),
                "volume": sum(
                    safe_int(item.get("volume"))
                    for item in items
                ),
                "last_oi": safe_int(
                    items[-1].get("oi")
                ),
                "bars": len(items),
            }
        )

    return output
