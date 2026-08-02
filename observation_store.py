from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable


DEFAULT_DB_PATH = "premium_intelligence_1m.db"


class ObservationStore:
    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
    ) -> None:
        self.connection = sqlite3.connect(Path(db_path))
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def __enter__(self) -> "ObservationStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS market_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                index_symbol TEXT NOT NULL,
                source TEXT NOT NULL,
                location TEXT NOT NULL,
                title TEXT NOT NULL,
                direction TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                detail TEXT NOT NULL,
                payload_json TEXT NOT NULL,

                UNIQUE(
                    timestamp,
                    index_symbol,
                    source,
                    location,
                    title,
                    direction
                )
            );

            CREATE INDEX IF NOT EXISTS idx_market_observations_latest
            ON market_observations (
                trading_date,
                index_symbol,
                timestamp
            );
            """
        )
        self.connection.commit()

    def save_many(
        self,
        observations: Iterable[dict[str, Any]],
    ) -> int:
        saved = 0

        for observation in observations:
            timestamp = str(
                observation.get("timestamp") or ""
            )

            if not timestamp:
                continue

            values = {
                "timestamp": timestamp,
                "trading_date": timestamp[:10],
                "index_symbol": str(
                    observation.get("index_symbol")
                    or "UNKNOWN"
                ),
                "source": str(
                    observation.get("source")
                    or "UNKNOWN"
                ),
                "location": str(
                    observation.get("location")
                    or "UNKNOWN"
                ),
                "title": str(
                    observation.get("title")
                    or "UNKNOWN"
                ),
                "direction": str(
                    observation.get("direction")
                    or "NEUTRAL"
                ),
                "value": float(
                    observation.get("value")
                    or 0.0
                ),
                "unit": str(
                    observation.get("unit")
                    or ""
                ),
                "detail": str(
                    observation.get("detail")
                    or ""
                ),
                "payload_json": json.dumps(
                    observation,
                    default=str,
                ),
            }

            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO market_observations (
                    timestamp,
                    trading_date,
                    index_symbol,
                    source,
                    location,
                    title,
                    direction,
                    value,
                    unit,
                    detail,
                    payload_json
                ) VALUES (
                    :timestamp,
                    :trading_date,
                    :index_symbol,
                    :source,
                    :location,
                    :title,
                    :direction,
                    :value,
                    :unit,
                    :detail,
                    :payload_json
                )
                """,
                values,
            )

            if cursor.rowcount > 0:
                saved += 1

        self.connection.commit()
        return saved
