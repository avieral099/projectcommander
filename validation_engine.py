from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")
DEFAULT_DB_PATH = "premium_intelligence_1m.db"
OUTCOME_WINDOWS = (5, 15, 30)


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _text(value: Any, default: str = "UNKNOWN") -> str:
    return str(value if value is not None else default).strip().upper()


def _timestamp(value: Any = None) -> str:
    if value:
        parsed = datetime.fromisoformat(str(value))
    else:
        parsed = datetime.now(IST)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    else:
        parsed = parsed.astimezone(IST)

    return parsed.replace(second=0, microsecond=0).isoformat()


class ValidationEngine:
    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def __enter__(self) -> "ValidationEngine":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trading_date TEXT NOT NULL,
                base_timestamp TEXT NOT NULL,
                index_symbol TEXT NOT NULL,

                base_spot REAL NOT NULL,
                base_atm_strike INTEGER NOT NULL,
                base_atm_straddle REAL NOT NULL,

                vwap_state TEXT NOT NULL,
                ema_structure TEXT NOT NULL,
                supertrend_state TEXT NOT NULL,
                or_status TEXT NOT NULL,
                driver_state TEXT NOT NULL,
                premium_flow_side TEXT NOT NULL,

                evidence_verdict TEXT NOT NULL,
                evidence_score REAL NOT NULL,
                call_confidence REAL NOT NULL,
                put_confidence REAL NOT NULL,
                engine_agreement INTEGER NOT NULL,

                lifecycle_state TEXT NOT NULL,
                lifecycle_action TEXT NOT NULL,
                instrument TEXT NOT NULL,
                instrument_price REAL NOT NULL,

                outcome_5m_timestamp TEXT,
                outcome_5m_spot REAL,
                outcome_5m_spot_change REAL,
                outcome_5m_straddle REAL,
                outcome_5m_straddle_change REAL,

                outcome_15m_timestamp TEXT,
                outcome_15m_spot REAL,
                outcome_15m_spot_change REAL,
                outcome_15m_straddle REAL,
                outcome_15m_straddle_change REAL,

                outcome_30m_timestamp TEXT,
                outcome_30m_spot REAL,
                outcome_30m_spot_change REAL,
                outcome_30m_straddle REAL,
                outcome_30m_straddle_change REAL,

                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                UNIQUE(base_timestamp, index_symbol)
            );

            CREATE INDEX IF NOT EXISTS idx_validation_pending
            ON validation_results (
                trading_date,
                index_symbol,
                base_timestamp
            );
            """
        )
        self.connection.commit()

    def capture(
        self,
        context: Any,
        *,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        snapshot = _get(context, "snapshot", {}) or {}
        evidence = _get(context, "evidence", {}) or {}
        lifecycle = _get(context, "lifecycle", {}) or {}
        recorder = _get(context, "recorder_result", {}) or {}

        base_timestamp = _timestamp(
            timestamp or _get(recorder, "timestamp")
        )
        trading_date = base_timestamp[:10]
        symbol = _text(_get(context, "symbol"), "UNKNOWN")

        payload = {
            "decision": _get(context, "decision", None),
            "lifecycle": lifecycle,
            "evidence": evidence,
            "snapshot": snapshot,
        }

        values = {
            "trading_date": trading_date,
            "base_timestamp": base_timestamp,
            "index_symbol": symbol,
            "base_spot": _float(snapshot.get("spot_price")),
            "base_atm_strike": _int(snapshot.get("atm_strike")),
            "base_atm_straddle": _float(
                snapshot.get("atm_straddle")
            ),
            "vwap_state": _text(
                _get(evidence, "vwap_state", "UNKNOWN")
            ),
            "ema_structure": _text(
                _get(evidence, "ema_structure", "UNKNOWN")
            ),
            "supertrend_state": _text(
                _get(evidence, "supertrend_state", "UNKNOWN")
            ),
            "or_status": _text(
                _get(evidence, "or_status", "UNKNOWN")
            ),
            "driver_state": _text(
                _get(evidence, "driver_state", "UNKNOWN")
            ),
            "premium_flow_side": _text(
                _get(evidence, "premium_flow_side", "BALANCED")
            ),
            "evidence_verdict": _text(
                _get(evidence, "verdict", "NO_BIAS")
            ),
            "evidence_score": _float(
                _get(evidence, "score", 0)
            ),
            "call_confidence": _float(
                _get(evidence, "call_confidence", 0)
            ),
            "put_confidence": _float(
                _get(evidence, "put_confidence", 0)
            ),
            "engine_agreement": _int(
                _get(evidence, "agreement", 0)
            ),
            "lifecycle_state": _text(
                _get(lifecycle, "state", "UNKNOWN")
            ),
            "lifecycle_action": _text(
                _get(lifecycle, "action", "WAIT")
            ),
            "instrument": _text(
                _get(lifecycle, "instrument", "NOT_SELECTED")
            ),
            "instrument_price": _float(
                _get(lifecycle, "current_price", 0)
            ),
            "payload_json": json.dumps(
                payload,
                default=str,
            ),
            "created_at": datetime.now(IST).isoformat(
                timespec="seconds"
            ),
            "updated_at": datetime.now(IST).isoformat(
                timespec="seconds"
            ),
        }

        self.connection.execute(
            """
            INSERT OR IGNORE INTO validation_results (
                trading_date,
                base_timestamp,
                index_symbol,
                base_spot,
                base_atm_strike,
                base_atm_straddle,
                vwap_state,
                ema_structure,
                supertrend_state,
                or_status,
                driver_state,
                premium_flow_side,
                evidence_verdict,
                evidence_score,
                call_confidence,
                put_confidence,
                engine_agreement,
                lifecycle_state,
                lifecycle_action,
                instrument,
                instrument_price,
                payload_json,
                created_at,
                updated_at
            ) VALUES (
                :trading_date,
                :base_timestamp,
                :index_symbol,
                :base_spot,
                :base_atm_strike,
                :base_atm_straddle,
                :vwap_state,
                :ema_structure,
                :supertrend_state,
                :or_status,
                :driver_state,
                :premium_flow_side,
                :evidence_verdict,
                :evidence_score,
                :call_confidence,
                :put_confidence,
                :engine_agreement,
                :lifecycle_state,
                :lifecycle_action,
                :instrument,
                :instrument_price,
                :payload_json,
                :created_at,
                :updated_at
            )
            """,
            values,
        )
        self.connection.commit()

        self.process_due(
            trading_date=trading_date,
            index_symbol=symbol,
            now=base_timestamp,
        )

        return {
            "status": "CAPTURED",
            "base_timestamp": base_timestamp,
            "index_symbol": symbol,
        }

    def process_due(
        self,
        *,
        trading_date: str,
        index_symbol: str,
        now: str | None = None,
    ) -> int:
        current = datetime.fromisoformat(_timestamp(now))
        updated = 0

        rows = self.connection.execute(
            """
            SELECT *
            FROM validation_results
            WHERE trading_date = ?
              AND index_symbol = ?
            ORDER BY base_timestamp
            """,
            (trading_date, index_symbol),
        ).fetchall()

        for row in rows:
            base_time = datetime.fromisoformat(
                row["base_timestamp"]
            )

            for minutes in OUTCOME_WINDOWS:
                timestamp_column = (
                    f"outcome_{minutes}m_timestamp"
                )

                if row[timestamp_column]:
                    continue

                target_time = base_time + timedelta(
                    minutes=minutes
                )

                if current < target_time:
                    continue

                outcome = self.connection.execute(
                    """
                    SELECT
                        timestamp,
                        spot_price,
                        atm_straddle
                    FROM intelligence_summaries
                    WHERE index_symbol = ?
                      AND timestamp >= ?
                    ORDER BY timestamp
                    LIMIT 1
                    """,
                    (
                        index_symbol,
                        target_time.isoformat(),
                    ),
                ).fetchone()

                if not outcome:
                    continue

                spot = _float(outcome["spot_price"])
                straddle = _float(outcome["atm_straddle"])

                self.connection.execute(
                    f"""
                    UPDATE validation_results
                    SET
                        outcome_{minutes}m_timestamp = ?,
                        outcome_{minutes}m_spot = ?,
                        outcome_{minutes}m_spot_change = ?,
                        outcome_{minutes}m_straddle = ?,
                        outcome_{minutes}m_straddle_change = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        outcome["timestamp"],
                        spot,
                        round(spot - row["base_spot"], 2),
                        straddle,
                        round(
                            straddle
                            - row["base_atm_straddle"],
                            2,
                        ),
                        datetime.now(IST).isoformat(
                            timespec="seconds"
                        ),
                        row["id"],
                    ),
                )
                updated += 1

        self.connection.commit()
        return updated
