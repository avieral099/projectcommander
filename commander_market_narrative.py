from __future__ import annotations

from typing import Any, Iterable


def _text(
    value: Any,
    default: str = "UNKNOWN",
) -> str:
    return str(
        value
        if value is not None
        else default
    ).strip()


def _event_names(
    events: Iterable[dict[str, Any]],
) -> set[str]:
    return {
        _text(
            event.get("event_name"),
            "UNKNOWN_EVENT",
        ).upper()
        for event in events
    }


def _direction(
    packet: dict[str, Any],
) -> str:
    return _text(
        packet.get("dominant_direction"),
        "NEUTRAL",
    ).upper()


def _confidence_label(
    confidence: float,
) -> str:
    if confidence >= 80:
        return "HIGH"

    if confidence >= 60:
        return "MODERATE"

    if confidence >= 40:
        return "DEVELOPING"

    return "LOW"


def _headline(
    names: set[str],
    direction: str,
) -> str:
    if {
        "ATM_STRADDLE_EXPANSION",
        "CALL_PREMIUM_PARTICIPATION",
    } <= names:
        return "Upside premium activity is expanding"

    if {
        "ATM_STRADDLE_EXPANSION",
        "PUT_PREMIUM_PARTICIPATION",
    } <= names:
        return "Downside premium activity is expanding"

    if {
        "VWAP_RECLAIM",
        "CALL_PREMIUM_PARTICIPATION",
    } <= names:
        return "Market structure is strengthening"

    if {
        "VWAP_LOSS",
        "PUT_PREMIUM_PARTICIPATION",
    } <= names:
        return "Market structure is weakening"

    if "ATM_STRADDLE_EXPANSION" in names:
        return "Combined ATM straddle premium is expanding"

    if "ATM_STRADDLE_CONTRACTION" in names:
        return "Combined ATM straddle premium is contracting"

    if "VWAP_RECLAIM" in names:
        return "Price has reclaimed VWAP"

    if "VWAP_LOSS" in names:
        return "Price has moved below VWAP"

    if direction in {"UP", "CALL"}:
        return "Market evidence is improving"

    if direction in {"DOWN", "PUT"}:
        return "Market evidence is weakening"

    if direction == "MIXED":
        return "Market evidence is mixed"

    return "No actionable market narrative"


def _summary(
    names: set[str],
    direction: str,
) -> str:
    parts: list[str] = []

    if "ATM_STRADDLE_EXPANSION" in names:
        parts.append(
            "Combined ATM call and put premium "
            "is expanding, showing increased "
            "movement or volatility."
        )

    if "ATM_STRADDLE_CONTRACTION" in names:
        parts.append(
            "Combined ATM call and put premium "
            "is contracting, showing continued "
            "premium compression."
        )

    if "CALL_PREMIUM_PARTICIPATION" in names:
        parts.append(
            "CALL premiums currently show "
            "stronger participation."
        )

    if "PUT_PREMIUM_PARTICIPATION" in names:
        parts.append(
            "PUT premiums currently show "
            "stronger participation."
        )

    if "VWAP_RECLAIM" in names:
        parts.append(
            "Price has reclaimed VWAP."
        )

    if "VWAP_LOSS" in names:
        parts.append(
            "Price has lost VWAP."
        )

    if "SUPERTREND_BULLISH_SHIFT" in names:
        parts.append(
            "Supertrend structure has shifted bullish."
        )

    if "SUPERTREND_BEARISH_SHIFT" in names:
        parts.append(
            "Supertrend structure has shifted bearish."
        )

    if parts:
        return " ".join(parts)

    if direction == "MIXED":
        return (
            "Current events do not agree on one "
            "clear market direction."
        )

    return "No actionable market events are active."


def _next_focus(
    names: set[str],
    direction: str,
) -> str:
    if "ATM_STRADDLE_EXPANSION" in names:
        if (
            "CALL_PREMIUM_PARTICIPATION" not in names
            and "PUT_PREMIUM_PARTICIPATION" not in names
        ):
            return (
                "Watch which option side gains "
                "participation during the expansion."
            )

        if (
            "VWAP_RECLAIM" not in names
            and "VWAP_LOSS" not in names
        ):
            return (
                "Watch whether market structure "
                "confirms the premium expansion."
            )

    if direction in {"UP", "CALL"}:
        if "SUPERTREND_BULLISH_SHIFT" not in names:
            return (
                "Watch for bullish Supertrend confirmation "
                "or rejection."
            )

    if direction in {"DOWN", "PUT"}:
        if "SUPERTREND_BEARISH_SHIFT" not in names:
            return (
                "Watch for bearish Supertrend confirmation "
                "or rejection."
            )

    if direction == "MIXED":
        return (
            "Wait for premium flow and market structure "
            "to align."
        )

    return "Continue monitoring for a meaningful state change."


def build_market_narrative(
    intelligence_packet: dict[str, Any],
) -> dict[str, Any]:
    events = (
        intelligence_packet.get(
            "supporting_events"
        )
        or []
    )

    names = _event_names(events)
    direction = _direction(
        intelligence_packet
    )

    confidence = float(
        intelligence_packet.get(
            "confidence"
        )
        or 0.0
    )

    risk = _text(
        intelligence_packet.get("risk"),
        "UNKNOWN",
    ).upper()

    status = _text(
        intelligence_packet.get("status"),
        "NO_ACTIONABLE_EVENTS",
    ).upper()

    if status != "ACTIONABLE":
        return {
            "status": "NO_ACTIONABLE_NARRATIVE",
            "headline": "No actionable market narrative",
            "summary": (
                "No actionable market events are active."
            ),
            "bias": "NEUTRAL",
            "confidence": round(confidence, 2),
            "confidence_label": "LOW",
            "risk": risk,
            "next_focus": (
                "Continue monitoring for a meaningful "
                "state change."
            ),
            "supporting_event_names": [],
        }

    return {
        "status": "ACTIONABLE",
        "headline": _headline(
            names,
            direction,
        ),
        "summary": _summary(
            names,
            direction,
        ),
        "bias": direction,
        "confidence": round(
            confidence,
            2,
        ),
        "confidence_label": _confidence_label(
            confidence
        ),
        "risk": risk,
        "next_focus": _next_focus(
            names,
            direction,
        ),
        "supporting_event_names": sorted(
            names
        ),
    }
