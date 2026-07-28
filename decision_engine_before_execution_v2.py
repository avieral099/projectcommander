from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Decision:
    action: str
    instrument: str
    conviction: float
    side: str
    entry_mode: str = "WAIT_FOR_TRIGGER"
    reasons: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def generate_decision(context: Any, *, minimum_confidence: float = 60.0) -> Decision:
    evidence = _get(context, "evidence", {}) or {}
    battle = _get(context, "battle", None)
    flow = _get(context, "flow", None)
    structure = _get(context, "structure", None)
    behaviour = _get(context, "behaviour", None)
    snapshot = _get(context, "snapshot", {}) or {}

    verdict = str(_get(evidence, "verdict", "NO_BIAS")).upper()
    call_confidence = _safe_float(_get(evidence, "call_confidence", 0.0))
    put_confidence = _safe_float(_get(evidence, "put_confidence", 0.0))
    battle_status = str(_get(battle, "commander_status", _get(battle, "status", "UNKNOWN"))).upper()
    flow_side = str(_get(flow, "dominant_side", "BALANCED")).upper()
    straddle_bias = str(_get(structure, "straddle_bias", "NEUTRAL")).upper()
    regime = str(_get(behaviour, "regime", "UNKNOWN")).upper()

    if "CALL" in verdict:
        side, confidence = "CALL", call_confidence
    elif "PUT" in verdict:
        side, confidence = "PUT", put_confidence
    elif call_confidence > put_confidence:
        side, confidence = "CALL", call_confidence
    elif put_confidence > call_confidence:
        side, confidence = "PUT", put_confidence
    else:
        side, confidence = "NEUTRAL", max(call_confidence, put_confidence)

    reasons = []
    blockers = []

    if side == "NEUTRAL":
        blockers.append("No directional evidence bias")

    if battle_status == "ATTACK":
        reasons.append("Battle engine authorised attack")
    else:
        blockers.append(f"Battle status is {battle_status}")

    if confidence >= minimum_confidence:
        reasons.append(f"Evidence confidence {confidence:.2f}%")
    else:
        blockers.append(f"Confidence below {minimum_confidence:.0f}%")

    if side in {"CALL", "PUT"}:
        if flow_side == side:
            reasons.append(f"Premium flow confirms {side}")
        elif flow_side == "BALANCED":
            blockers.append("Premium flow is balanced")
        else:
            blockers.append(f"Premium flow conflicts: {flow_side}")

    if side in {"CALL", "PUT"}:
        if straddle_bias in {"LONG_STRADDLE", side, "NEUTRAL"}:
            reasons.append(f"Straddle bias permits {side}")
        else:
            blockers.append(f"Straddle bias conflicts: {straddle_bias}")

    if regime in {"PREMIUM_EXPANSION", "ROTATION_WITH_EXPANSION", "PREMIUM_MIGRATION_DAY", "MIXED_PREMIUM_REGIME"}:
        reasons.append(f"Premium regime: {regime}")

    if blockers:
        return Decision(
            action="NO_TRADE",
            instrument="NOT_SELECTED",
            conviction=round(confidence, 2),
            side=side,
            entry_mode="WAIT",
            reasons=reasons,
            blockers=blockers,
        )

    strike = int(_safe_float(_get(snapshot, "atm_strike", 0)))
    option_type = "CE" if side == "CALL" else "PE"
    instrument = f"{strike} {option_type}" if strike > 0 else "NOT_SELECTED"

    return Decision(
        action="BUY_CALL" if side == "CALL" else "BUY_PUT",
        instrument=instrument,
        conviction=round(confidence, 2),
        side=side,
        entry_mode="WAIT_FOR_PREMIUM_TRIGGER",
        reasons=reasons,
        blockers=[],
    )
