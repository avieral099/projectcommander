from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


def _text(value: Any, default: str = "UNKNOWN") -> str:
    return str(value if value is not None else default).strip()


def _direction(event: dict[str, Any]) -> str:
    return _text(
        event.get("current_direction"),
        "NEUTRAL",
    ).upper()


def _severity(event: dict[str, Any]) -> str:
    return _text(
        event.get("severity"),
        "INFO",
    ).upper()


def _priority(event: dict[str, Any]) -> int:
    try:
        return int(event.get("priority_score") or 0)
    except (TypeError, ValueError):
        return 0


def _confidence(events: list[dict[str, Any]]) -> int:
    if not events:
        return 0

    priority_component = min(
        sum(_priority(event) for event in events) * 8,
        50,
    )

    directions = [
        _direction(event)
        for event in events
        if _direction(event) not in {"NEUTRAL", "UNKNOWN"}
    ]

    agreement_component = 0

    if directions:
        counts = Counter(directions)
        dominant_count = counts.most_common(1)[0][1]
        agreement_component = round(
            dominant_count / len(directions) * 30
        )

    breadth_component = min(len(events) * 5, 20)

    return min(
        priority_component
        + agreement_component
        + breadth_component,
        100,
    )


def _dominant_direction(
    events: list[dict[str, Any]],
) -> str:
    directions = [
        _direction(event)
        for event in events
        if _direction(event) not in {"NEUTRAL", "UNKNOWN"}
    ]

    if not directions:
        return "NEUTRAL"

    counts = Counter(directions)
    top = counts.most_common()

    if len(top) > 1 and top[0][1] == top[1][1]:
        return "MIXED"

    return top[0][0]


def _market_story(
    events: list[dict[str, Any]],
    dominant_direction: str,
) -> str:
    locations = {
        _text(event.get("location")).upper()
        for event in events
    }

    has_straddle = "ATM_STRADDLE" in locations
    has_flow = "PREMIUM_FLOW" in locations
    has_vwap = "VWAP" in locations
    has_supertrend = "SUPERTREND" in locations

    if (
        has_straddle
        and has_flow
        and (
            has_vwap
            or has_supertrend
        )
    ):
        if dominant_direction in {"UP", "CALL"}:
            return (
                "Premium expansion is aligning with "
                "improving market structure."
            )

        if dominant_direction in {"DOWN", "PUT"}:
            return (
                "Premium expansion is aligning with "
                "weakening market structure."
            )

        return (
            "Premium and market structure are changing "
            "together, but direction is mixed."
        )

    if has_straddle and has_flow:
        return (
            "Option premium activity is increasing and "
            "one side is gaining participation."
        )

    if has_vwap and has_supertrend:
        return (
            "Market structure has shifted across multiple "
            "trend references."
        )

    if has_straddle:
        return (
            "ATM straddle behaviour has changed materially."
        )

    if has_flow:
        return (
            "Premium participation has shifted between "
            "CALL and PUT."
        )

    if events:
        return events[0].get(
            "display_text",
            "Market conditions changed.",
        )

    return "No actionable market intelligence."


def _risk_label(
    events: list[dict[str, Any]],
    dominant_direction: str,
) -> str:
    severities = {
        _severity(event)
        for event in events
    }

    if "CRITICAL" in severities:
        return "HIGH"

    if dominant_direction == "MIXED":
        return "HIGH"

    if "URGENT" in severities:
        return "ELEVATED"

    if "IMPORTANT" in severities:
        return "MODERATE"

    return "LOW"


def build_intelligence_packet(
    events: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    ordered = sorted(
        list(events),
        key=lambda event: (
            _priority(event),
            _text(event.get("timestamp")),
            int(event.get("id") or 0),
        ),
        reverse=True,
    )

    dominant_direction = _dominant_direction(ordered)
    confidence = _confidence(ordered)
    risk = _risk_label(
        ordered,
        dominant_direction,
    )

    highest_priority = (
        _priority(ordered[0])
        if ordered
        else 0
    )

    highest_severity = (
        _severity(ordered[0])
        if ordered
        else "INFO"
    )

    return {
        "status": (
            "ACTIONABLE"
            if ordered
            else "NO_ACTIONABLE_EVENTS"
        ),
        "event_count": len(ordered),
        "dominant_direction": dominant_direction,
        "confidence": confidence,
        "risk": risk,
        "highest_priority": highest_priority,
        "highest_severity": highest_severity,
        "market_story": _market_story(
            ordered,
            dominant_direction,
        ),
        "supporting_event_ids": [
            int(event.get("id") or 0)
            for event in ordered
        ],
        "supporting_events": ordered,
    }
