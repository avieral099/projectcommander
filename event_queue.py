from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = "premium_intelligence_1m.db"


class EventQueue:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.connection = sqlite3.connect(Path(db_path))
        self.connection.row_factory = sqlite3.Row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.connection.close()

    def latest(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM market_events
            WHERE status='NEW'
            ORDER BY
                priority_score DESC,
                timestamp DESC,
                id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [dict(r) for r in rows]


    def acknowledge(
        self,
        event_id: int,
    ) -> None:
        self.connection.execute(
            """
            UPDATE market_events
            SET status='ACKNOWLEDGED'
            WHERE id=?
            """,
            (event_id,),
        )
        self.connection.commit()


    def acknowledge_many(
        self,
        event_ids: list[int],
    ) -> int:
        ids = [
            int(event_id)
            for event_id in event_ids
            if int(event_id) > 0
        ]

        if not ids:
            return 0

        placeholders = ",".join(
            "?"
            for _ in ids
        )

        cursor = self.connection.execute(
            f"""
            UPDATE market_events
            SET status='ACKNOWLEDGED'
            WHERE id IN ({placeholders})
              AND status='NEW'
            """,
            ids,
        )

        self.connection.commit()
        return cursor.rowcount


    def summary(self) -> dict[str, int]:
        rows = self.connection.execute(
            """
            SELECT
                severity,
                COUNT(*) AS event_count
            FROM market_events
            WHERE status='NEW'
            GROUP BY severity
            """
        ).fetchall()

        summary = {
            "CRITICAL": 0,
            "URGENT": 0,
            "IMPORTANT": 0,
            "WATCH": 0,
            "INFO": 0,
            "TOTAL": 0,
        }

        for row in rows:
            severity = str(row["severity"] or "INFO").upper()
            count = int(row["event_count"] or 0)

            if severity not in summary:
                severity = "INFO"

            summary[severity] += count
            summary["TOTAL"] += count

        return summary


    def latest_actionable(
        self,
        limit: int = 20,
        minimum_priority: int = 2,
    ) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM market_events
            WHERE status='NEW'
              AND priority_score >= ?
            ORDER BY
                priority_score DESC,
                timestamp DESC,
                id DESC
            LIMIT ?
            """,
            (
                int(minimum_priority),
                int(limit),
            ),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]
