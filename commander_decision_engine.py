from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


VALID_REGIMES = {
    "BULLISH",
    "BULLISH_BIAS",
    "MIXED",
    "BEARISH_BIAS",
    "BEARISH",
}


def _f(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _quality(confidence: float, risk: str) -> str:
    if risk == "HIGH":
        if confidence >= 80:
            return "B"
        if confidence >= 65:
            return "C"
        return "NO_TRADE"

    if risk == "ELEVATED":
        if confidence >= 82:
            return "A"
        if confidence >= 70:
            return "B"
        if confidence >= 58:
            return "C"
        return "NO_TRADE"

    if confidence >= 85:
        return "A+"
    if confidence >= 75:
        return "A"
    if confidence >= 65:
        return "B"
    if confidence >= 55:
        return "C"
    return "NO_TRADE"


def _market_action(regime: str, confidence: float, risk: str) -> str:
    """
    This is a market-context action, not an order instruction.
    """
    if risk == "HIGH":
        return "OBSERVE_ONLY"

    if regime == "BULLISH" and confidence >= 70:
        return "LOOK_FOR_BULLISH_CONFIRMATION"
    if regime == "BULLISH_BIAS" and confidence >= 60:
        return "BULLISH_WATCH"
    if regime == "BEARISH" and confidence >= 70:
        return "LOOK_FOR_BEARISH_CONFIRMATION"
    if regime == "BEARISH_BIAS" and confidence >= 60:
        return "BEARISH_WATCH"

    return "WAIT_FOR_CLEAR_STRUCTURE"


def analyse_decision(market_health: dict[str, Any]) -> dict[str, Any]:
    regime = str(market_health.get("regime", "MIXED")).upper()
    if regime not in VALID_REGIMES:
        regime = "MIXED"

    bull_score = _f(market_health.get("bull_score"))
    bear_score = _f(market_health.get("bear_score"))
    risk = str(market_health.get("risk", "HIGH")).upper()
    breadth = str(market_health.get("breadth", "WEAK")).upper()
    momentum = str(market_health.get("momentum", "BALANCED")).upper()
    trend = str(market_health.get("trend", "TRANSITION")).upper()

    direction_score = max(bull_score, bear_score)
    agreement_bonus = 0.0
    penalties = 0.0

    if breadth == "STRONG":
        agreement_bonus += 7.0
    elif breadth == "WEAK":
        penalties += 6.0

    if regime.startswith("BULL") and momentum == "IMPROVING":
        agreement_bonus += 6.0
    elif regime.startswith("BEAR") and momentum == "WEAKENING":
        agreement_bonus += 6.0
    elif momentum == "BALANCED":
        penalties += 2.0

    if trend == "HEALTHY" and regime.startswith("BULL"):
        agreement_bonus += 5.0
    elif trend == "DAMAGED" and regime.startswith("BEAR"):
        agreement_bonus += 5.0
    elif trend == "TRANSITION":
        penalties += 5.0

    if risk == "ELEVATED":
        penalties += 8.0
    elif risk == "HIGH":
        penalties += 18.0

    confidence = max(0.0, min(100.0, direction_score + agreement_bonus - penalties))
    action = _market_action(regime, confidence, risk)
    quality = _quality(confidence, risk)

    why: list[str] = []
    warnings = list(market_health.get("warnings", []))

    if regime.startswith("BULL"):
        why.append(f"Bull structure leads {bull_score:.2f} versus bear {bear_score:.2f}.")
    elif regime.startswith("BEAR"):
        why.append(f"Bear structure leads {bear_score:.2f} versus bull {bull_score:.2f}.")
    else:
        why.append("Bull and bear structure remain too close for directional conviction.")

    why.append(f"Breadth is {breadth.lower()}.")
    why.append(f"Momentum is {momentum.lower()} and trend is {trend.lower()}.")

    participation = _f(market_health.get("participation_pct"))
    vwap = _f(market_health.get("vwap_pct"))
    pdc = _f(market_health.get("pdc_pct"))
    bull_stack = _f(market_health.get("bullish_stack_pct"))
    bear_stack = _f(market_health.get("bearish_stack_pct"))

    why.append(
        f"Participation {participation:.2f}% | VWAP {vwap:.2f}% | PDC {pdc:.2f}%."
    )
    why.append(
        f"Bull stacks {bull_stack:.2f}% versus bear stacks {bear_stack:.2f}%."
    )

    blockers: list[str] = []
    if risk == "HIGH":
        blockers.append("Market-health risk is HIGH.")
    if breadth == "WEAK":
        blockers.append("Breadth is weak.")
    if trend == "TRANSITION":
        blockers.append("Trend remains in transition.")
    if confidence < 60:
        blockers.append("Confidence is below 60.")
    if action == "WAIT_FOR_CLEAR_STRUCTURE":
        blockers.append("No clean directional structure.")
    if action == "OBSERVE_ONLY":
        blockers.append("Observation only until risk falls.")

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_generated_at": market_health.get("generated_at"),
        "universe": market_health.get("universe", "UNKNOWN"),
        "scanned": market_health.get("scanned", 0),
        "total": market_health.get("total", 0),
        "regime": regime,
        "confidence": round(confidence, 2),
        "quality": quality,
        "risk": risk,
        "market_action": action,
        "directional_side": (
            "BULL"
            if bull_score > bear_score
            else "BEAR"
            if bear_score > bull_score
            else "NEUTRAL"
        ),
        "bull_score": round(bull_score, 2),
        "bear_score": round(bear_score, 2),
        "breadth": breadth,
        "momentum": momentum,
        "trend": trend,
        "why": why,
        "warnings": warnings,
        "blockers": blockers,
        "execution_allowed": False,
        "execution_note": (
            "Decision V1 describes market context only. "
            "Premium and driver confirmation are not connected yet."
        ),
    }


def generate_decision(
    health_path: str | Path = "market_health_snapshot.json",
    output_path: str | Path = "commander_decision_snapshot.json",
) -> dict[str, Any]:
    health_path = Path(health_path)
    if not health_path.exists():
        raise FileNotFoundError(f"Market-health snapshot not found: {health_path}")

    health = json.loads(health_path.read_text(encoding="utf-8"))
    decision = analyse_decision(health)

    Path(output_path).write_text(
        json.dumps(decision, indent=2),
        encoding="utf-8",
    )
    return decision
