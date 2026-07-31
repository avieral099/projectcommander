"""
OPERATION COMMANDER
Module  : Reference Lock Engine V1
Purpose : 09:21 battle reference aur 09:25 short-straddle reference
          ko idempotently SQLite mein lock karna.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")
DEFAULT_DB_PATH = "premium_intelligence_1m.db"

REFERENCE_0921 = "BATTLE_0921"
REFERENCE_0925 = "STRADDLE_0925"


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


def normalise_datetime(
    value: Optional[str | datetime] = None,
) -> datetime:
    if value is None:
        return datetime.now(IST)

    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value))

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    else:
        parsed = parsed.astimezone(IST)

    return parsed


@dataclass(frozen=True)
class ReferenceLock:
    trading_date: str
    lock_time: str
    reference_type: str
    index_symbol: str
    expiry_date: str
    atm_strike: int
    spot_price: float
    atm_ce: float
    atm_pe: float
    atm_straddle: float
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReferenceLockEngine:
    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def __enter__(self) -> "ReferenceLockEngine":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS commander_reference_locks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trading_date TEXT NOT NULL,
                lock_time TEXT NOT NULL,
                reference_type TEXT NOT NULL,
                index_symbol TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                atm_strike INTEGER NOT NULL,
                spot_price REAL NOT NULL,
                atm_ce REAL NOT NULL,
                atm_pe REAL NOT NULL,
                atm_straddle REAL NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(
                    trading_date,
                    reference_type,
                    index_symbol,
                    expiry_date
                )
            );

            CREATE INDEX IF NOT EXISTS idx_commander_reference_lookup
            ON commander_reference_locks (
                trading_date,
                index_symbol,
                expiry_date,
                reference_type
            );
            """
        )
        self.connection.commit()

    def get_lock(
        self,
        *,
        trading_date: str,
        reference_type: str,
        index_symbol: str,
        expiry_date: str,
    ) -> Optional[Dict[str, Any]]:
        row = self.connection.execute(
            """
            SELECT *
            FROM commander_reference_locks
            WHERE trading_date = ?
              AND reference_type = ?
              AND index_symbol = ?
              AND expiry_date = ?
            LIMIT 1
            """,
            (
                trading_date,
                reference_type,
                index_symbol,
                expiry_date,
            ),
        ).fetchone()

        if not row:
            return None

        result = dict(row)

        try:
            result["payload"] = json.loads(
                result.get("payload_json") or "{}"
            )
        except json.JSONDecodeError:
            result["payload"] = {}

        return result

    def save_lock(
        self,
        lock: ReferenceLock,
        *,
        created_at: str,
    ) -> Dict[str, Any]:
        self.connection.execute(
            """
            INSERT OR IGNORE INTO commander_reference_locks (
                trading_date,
                lock_time,
                reference_type,
                index_symbol,
                expiry_date,
                atm_strike,
                spot_price,
                atm_ce,
                atm_pe,
                atm_straddle,
                payload_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lock.trading_date,
                lock.lock_time,
                lock.reference_type,
                lock.index_symbol,
                lock.expiry_date,
                lock.atm_strike,
                lock.spot_price,
                lock.atm_ce,
                lock.atm_pe,
                lock.atm_straddle,
                json.dumps(lock.payload, default=str),
                created_at,
            ),
        )
        self.connection.commit()

        return self.get_lock(
            trading_date=lock.trading_date,
            reference_type=lock.reference_type,
            index_symbol=lock.index_symbol,
            expiry_date=lock.expiry_date,
        ) or {}

    def maybe_lock(
        self,
        *,
        reference_type: str,
        target_time: time,
        index_symbol: str,
        premium_snapshot: Mapping[str, Any],
        market_snapshot: Optional[Mapping[str, Any]] = None,
        behaviour: Any = None,
        flow: Any = None,
        structure: Any = None,
        battle: Any = None,
        now: Optional[str | datetime] = None,
    ) -> Dict[str, Any]:
        current = normalise_datetime(now)
        trading_date = current.date().isoformat()
        expiry_date = str(
            premium_snapshot.get("expiry_date") or "UNKNOWN"
        )

        existing = self.get_lock(
            trading_date=trading_date,
            reference_type=reference_type,
            index_symbol=index_symbol,
            expiry_date=expiry_date,
        )

        if existing:
            return {
                "status": "ALREADY_LOCKED",
                "reference": existing,
            }

        current_clock = current.time().replace(tzinfo=None)

        if current_clock < target_time:
            return {
                "status": "AWAITING_LOCK_TIME",
                "target_time": target_time.strftime("%H:%M"),
                "reference": None,
            }

        if current_clock > target_time:
            target_clock = target_time.strftime("%H:%M")

            row = self.connection.execute(
                """
                SELECT
                    timestamp,
                    trading_date,
                    index_symbol,
                    expiry_date,
                    spot_price,
                    atm_strike,
                    ce_ltp,
                    pe_ltp,
                    straddle
                FROM strike_straddle_minute_bars
                WHERE trading_date = ?
                  AND index_symbol = ?
                  AND substr(timestamp, 12, 5) = ?
                  AND strike = atm_strike
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (
                    trading_date,
                    index_symbol,
                    target_clock,
                ),
            ).fetchone()

            if not row:
                return {
                    "status": "MISSED_LOCK_NO_SOURCE",
                    "target_time": target_clock,
                    "reference": None,
                }

            recovered = ReferenceLock(
                trading_date=row["trading_date"],
                lock_time=target_clock,
                reference_type=reference_type,
                index_symbol=row["index_symbol"],
                expiry_date=row["expiry_date"],
                atm_strike=safe_int(row["atm_strike"]),
                spot_price=safe_float(row["spot_price"]),
                atm_ce=round(safe_float(row["ce_ltp"]), 2),
                atm_pe=round(safe_float(row["pe_ltp"]), 2),
                atm_straddle=round(
                    safe_float(row["straddle"]),
                    2,
                ),
                payload={
                    "recovered": True,
                    "source_table": (
                        "strike_straddle_minute_bars"
                    ),
                    "source_timestamp": row["timestamp"],
                },
            )

            saved = self.save_lock(
                recovered,
                created_at=current.isoformat(
                    timespec="seconds"
                ),
            )

            return {
                "status": "RECOVERED_LOCK",
                "reference": saved,
            }

        contracts = premium_snapshot.get("contracts") or {}
        atm_ce_contract = contracts.get("ATM_CE") or {}
        atm_pe_contract = contracts.get("ATM_PE") or {}

        atm_ce = safe_float(atm_ce_contract.get("ltp"))
        atm_pe = safe_float(atm_pe_contract.get("ltp"))
        atm_straddle = safe_float(
            premium_snapshot.get("atm_straddle"),
            atm_ce + atm_pe,
        )

        def read_value(obj: Any, name: str, default: Any = None) -> Any:
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        payload = {
            "market_snapshot": dict(market_snapshot or {}),
            "premium": dict(premium_snapshot),
            "behaviour": {
                "regime": read_value(behaviour, "regime"),
                "commander_view": read_value(
                    behaviour,
                    "commander_view",
                ),
            },
            "flow": {
                "dominant_side": read_value(
                    flow,
                    "dominant_side",
                ),
                "dominant_flow": read_value(
                    flow,
                    "dominant_flow",
                ),
                "call_leader_display": read_value(
                    flow,
                    "call_leader_display",
                ),
                "put_leader_display": read_value(
                    flow,
                    "put_leader_display",
                ),
                "atm_erosion_destination": read_value(
                    flow,
                    "atm_erosion_destination",
                ),
            },
            "structure": {
                "structure_state": read_value(
                    structure,
                    "structure_state",
                ),
                "straddle_bias": read_value(
                    structure,
                    "straddle_bias",
                ),
                "short_straddle_stance": read_value(
                    structure,
                    "short_straddle_stance",
                ),
            },
            "battle": {
                "zone": read_value(battle, "zone"),
                "battle_score": read_value(
                    battle,
                    "battle_score",
                ),
                "commander_status": read_value(
                    battle,
                    "commander_status",
                ),
            },
        }

        lock = ReferenceLock(
            trading_date=trading_date,
            lock_time=target_time.strftime("%H:%M"),
            reference_type=reference_type,
            index_symbol=index_symbol,
            expiry_date=expiry_date,
            atm_strike=safe_int(
                premium_snapshot.get("atm_strike")
            ),
            spot_price=safe_float(
                premium_snapshot.get("spot_price")
            ),
            atm_ce=round(atm_ce, 2),
            atm_pe=round(atm_pe, 2),
            atm_straddle=round(atm_straddle, 2),
            payload=payload,
        )

        saved = self.save_lock(
            lock,
            created_at=current.isoformat(timespec="seconds"),
        )

        return {
            "status": "LOCKED",
            "reference": saved,
        }

    def process_session_locks(
        self,
        *,
        index_symbol: str,
        premium_snapshot: Mapping[str, Any],
        market_snapshot: Optional[Mapping[str, Any]] = None,
        behaviour: Any = None,
        flow: Any = None,
        structure: Any = None,
        battle: Any = None,
        now: Optional[str | datetime] = None,
    ) -> Dict[str, Any]:
        common = {
            "index_symbol": index_symbol,
            "premium_snapshot": premium_snapshot,
            "market_snapshot": market_snapshot,
            "behaviour": behaviour,
            "flow": flow,
            "structure": structure,
            "battle": battle,
            "now": now,
        }

        return {
            "battle_0921": self.maybe_lock(
                reference_type=REFERENCE_0921,
                target_time=time(9, 21),
                **common,
            ),
            "straddle_0925": self.maybe_lock(
                reference_type=REFERENCE_0925,
                target_time=time(9, 25),
                **common,
            ),
        }
