from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from commander_state_store import read_state

DEFAULT_STATE_FILE = "commander_state.json"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


class DashboardStateAdapter:
    """
    Read-only adapter between Commander CPU state and frontend renderers.

    V1 does not alter dashboard calculations yet. It provides a safe,
    consistent interface for incrementally migrating dashboard sections
    to commander_state.json.
    """

    def __init__(
        self,
        state_file: str | Path = DEFAULT_STATE_FILE,
    ) -> None:
        self.state_file = Path(state_file)
        self.state: dict[str, Any] = {}

    def refresh(self) -> dict[str, Any]:
        self.state = _dict(
            read_state(self.state_file)
        )
        return self.state

    @property
    def available(self) -> bool:
        return bool(self.state)

    @property
    def timestamp(self) -> str:
        return str(
            self.state.get("updated_at")
            or self.state.get("generated_at")
            or self.state.get("timestamp")
            or ""
        )

    @property
    def age_seconds(self) -> float | None:
        timestamp = _parse_timestamp(self.timestamp)

        if timestamp is None:
            return None

        now = datetime.now(timestamp.tzinfo)
        return max(
            0.0,
            (now - timestamp).total_seconds(),
        )

    def is_fresh(
        self,
        maximum_age_seconds: float = 120.0,
    ) -> bool:
        age = self.age_seconds

        return (
            self.available
            and age is not None
            and age <= maximum_age_seconds
        )

    @property
    def phase(self) -> str:
        return str(
            self.state.get("phase")
            or "UNKNOWN"
        )

    @property
    def market_snapshots(self) -> dict[str, Any]:
        return _dict(
            self.state.get("market_snapshots")
        )

    @property
    def premium_snapshots(self) -> dict[str, Any]:
        return _dict(
            self.state.get("premium_snapshots")
        )

    @property
    def drivers(self) -> dict[str, Any]:
        return _dict(
            self.state.get("drivers")
        )

    @property
    def contexts(self) -> dict[str, Any]:
        return _dict(
            self.state.get("contexts")
        )

    @property
    def system_statuses(self) -> dict[str, Any]:
        return _dict(
            self.state.get("system_statuses")
        )

    @property
    def watchlist(self) -> dict[str, Any]:
        return _dict(
            self.state.get("watchlist")
        )

    @property
    def event_queue_summary(self) -> dict[str, Any]:
        return _dict(
            self.state.get("event_queue_summary")
        )

    @property
    def actionable_events(self) -> list[dict[str, Any]]:
        return [
            _dict(event)
            for event in _list(
                self.state.get("actionable_events")
            )
        ]

    @property
    def intelligence_packet(self) -> dict[str, Any]:
        packet = _dict(
            self.state.get("intelligence_packet")
        )

        if packet:
            return packet

        return {
            "status": "UNAVAILABLE",
            "event_count": 0,
            "dominant_direction": "NEUTRAL",
            "confidence": 0,
            "risk": "UNKNOWN",
            "highest_priority": 0,
            "highest_severity": "INFO",
            "market_story": (
                "Commander intelligence state unavailable."
            ),
            "supporting_event_ids": [],
            "supporting_events": [],
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "fresh": self.is_fresh(),
            "timestamp": self.timestamp,
            "age_seconds": self.age_seconds,
            "phase": self.phase,
            "market_snapshots": self.market_snapshots,
            "premium_snapshots": self.premium_snapshots,
            "drivers": self.drivers,
            "contexts": self.contexts,
            "system_statuses": self.system_statuses,
            "watchlist": self.watchlist,
            "event_queue_summary": self.event_queue_summary,
            "actionable_events": self.actionable_events,
            "intelligence_packet": self.intelligence_packet,
        }
