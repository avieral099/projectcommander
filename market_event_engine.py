from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable


DEFAULT_DB_PATH = "premium_intelligence_1m.db"


def _text(value: Any, default: str = "UNKNOWN") -> str:
    return str(value if value is not None else default).strip()


class MarketEventEngine:
    """
    Convert repeated observations into state-change events.

    V1 rule:
    - First observation establishes baseline.
    - Same state is ignored.
    - Changed state creates one event.
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
    ) -> None:
        self.connection = sqlite3.connect(Path(db_path))
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def __enter__(self) -> "MarketEventEngine":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS market_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                index_symbol TEXT NOT NULL,
                source TEXT NOT NULL,
                location TEXT NOT NULL,

                previous_title TEXT NOT NULL,
                current_title TEXT NOT NULL,
                previous_direction TEXT NOT NULL,
                current_direction TEXT NOT NULL,

                event_type TEXT NOT NULL,
                display_text TEXT NOT NULL,
                status TEXT NOT NULL,

                UNIQUE(
                    timestamp,
                    index_symbol,
                    source,
                    location,
                    event_type
                )
            );

            CREATE INDEX IF NOT EXISTS idx_market_events_latest
            ON market_events (
                trading_date,
                index_symbol,
                timestamp
            );
            """
        )
        self.connection.commit()

    def _previous_observation(
        self,
        observation: dict[str, Any],
    ) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT
                timestamp,
                title,
                direction,
                value,
                unit,
                detail
            FROM market_observations
            WHERE index_symbol = ?
              AND source = ?
              AND location = ?
              AND timestamp < ?
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
            """,
            (
                observation["index_symbol"],
                observation["source"],
                observation["location"],
                observation["timestamp"],
            ),
        ).fetchone()

        return dict(row) if row else None

    def detect(
        self,
        observations: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        for current in observations:
            previous = self._previous_observation(current)

            # First row is baseline, not an event.
            if not previous:
                continue

            previous_title = _text(previous.get("title"))
            current_title = _text(current.get("title"))

            previous_direction = _text(
                previous.get("direction"),
                "NEUTRAL",
            )
            current_direction = _text(
                current.get("direction"),
                "NEUTRAL",
            )

            if (
                previous_title == current_title
                and previous_direction == current_direction
            ):
                continue

            if previous_direction != current_direction:
                event_type = "DIRECTION_CHANGED"
            else:
                event_type = "STATE_CHANGED"

            display_text = (
                f"{current['location']}: "
                f"{previous_title} → {current_title}"
            )

            event = {
                "timestamp": current["timestamp"],
                "trading_date": current["timestamp"][:10],
                "index_symbol": current["index_symbol"],
                "source": current["source"],
                "location": current["location"],
                "previous_title": previous_title,
                "current_title": current_title,
                "previous_direction": previous_direction,
                "current_direction": current_direction,
                "event_type": event_type,
                "display_text": display_text,
                "status": "NEW",
            }

            events.append(event)

        return events

    def save_many(
        self,
        events: Iterable[dict[str, Any]],
    ) -> int:
        saved = 0

        for event in events:
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO market_events (
                    timestamp,
                    trading_date,
                    index_symbol,
                    source,
                    location,
                    previous_title,
                    current_title,
                    previous_direction,
                    current_direction,
                    event_type,
                    display_text,
                    status
                ) VALUES (
                    :timestamp,
                    :trading_date,
                    :index_symbol,
                    :source,
                    :location,
                    :previous_title,
                    :current_title,
                    :previous_direction,
                    :current_direction,
                    :event_type,
                    :display_text,
                    :status
                )
                """,
                event,
            )

            if cursor.rowcount > 0:
                saved += 1

        self.connection.commit()
        return saved

    def process(
        self,
        observations: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        events = self.detect(observations)
        self.save_many(events)
        return events
