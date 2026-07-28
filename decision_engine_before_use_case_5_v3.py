from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass
class Decision:
    action: str
    instrument: str
    conviction: float
    side: str
    entry_mode: str = "WAIT_FOR_PREMIUM_TRIGGER"
    strike_label: str = "NOT_SELECTED"
    entry_reference: float = 0.0
    stop_loss: float = 0.0
    target_1: float = 0.0
    target_2: float = 0.0
    target_3: float = 0.0
    trail_reference: str = "SUPERTREND_OR_EMA75_LOW"
    reasons: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)


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


def _text(value: Any, default: str) -> str:
    return str(value or default).strip().upper()


def _contract_price(contract: Any) -> float:
    ask = _float(_get(contract, "ask", 0.0))
    ltp = _float(_get(contract, "ltp", 0.0))
    return ask if ask > 0 else ltp


def _select_contract(snapshot: Any, side: str, confidence: float):
    contracts = _get(snapshot, "contracts", {}) or {}
    suffix = "CE" if side == "CALL" else "PE"

    if confidence >= 75:
        order = (f"ATM_{suffix}", f"ITM1_{suffix}", f"OTM1_{suffix}")
    else:
        order = (f"ITM1_{suffix}", f"ATM_{suffix}", f"OTM1_{suffix}")

    for label in order:
        contract = contracts.get(label)
        if contract and _contract_price(contract) > 0:
            return label, contract

    return "NOT_SELECTED", None


def _levels(entry: float) -> dict[str, float]:
    if entry <= 0:
        return {"sl": 0.0, "t1": 0.0, "t2": 0.0, "t3": 0.0}

    return {
        "sl": round(entry * 0.85, 2),
        "t1": round(entry * 1.20, 2),
        "t2": round(entry * 1.35, 2),
        "t3": round(entry * 1.50, 2),
    }


def generate_decision(context: Any, *, minimum_confidence: float = 60.0) -> Decision:
    evidence = _get(context, "evidence", {}) or {}
    battle = _get(context, "battle", None)
    flow = _get(context, "flow", None)
    structure = _get(context, "structure", None)
    behaviour = _get(context, "behaviour", None)
    snapshot = _get(context, "snapshot", {}) or {}

    verdict = _text(_get(evidence, "verdict", "NO_BIAS"), "NO_BIAS")
    call_confidence = _float(_get(evidence, "call_confidence", 0.0))
    put_confidence = _float(_get(evidence, "put_confidence", 0.0))

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

    battle_status = _text(
        _get(battle, "commander_status", _get(battle, "status", "UNKNOWN")),
        "UNKNOWN",
    )
    battle_score = _float(
        _get(battle, "battle_score", _get(battle, "score", 0.0))
    )
    flow_side = _text(_get(flow, "dominant_side", "BALANCED"), "BALANCED")
    straddle_bias = _text(_get(structure, "straddle_bias", "NEUTRAL"), "NEUTRAL")
    structure_state = _text(_get(structure, "structure_state", "UNKNOWN"), "UNKNOWN")
    regime = _text(_get(behaviour, "regime", "UNKNOWN"), "UNKNOWN")

    reasons = []
    blockers = []

    if side == "NEUTRAL":
        blockers.append("No directional evidence bias")

    if battle_status == "ATTACK":
        reasons.append(f"Battle authorised ATTACK; score {battle_score:.2f}")
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
        if straddle_bias in {"NEUTRAL", "LONG_STRADDLE", side}:
            reasons.append(f"Straddle bias permits {side}")
        else:
            blockers.append(f"Straddle bias conflicts: {straddle_bias}")

    if structure_state != "UNKNOWN":
        reasons.append(f"Straddle structure: {structure_state}")

    if regime != "UNKNOWN":
        reasons.append(f"Premium regime: {regime}")

    label, contract = (
        _select_contract(snapshot, side, confidence)
        if side in {"CALL", "PUT"}
        else ("NOT_SELECTED", None)
    )

    entry = _contract_price(contract) if contract else 0.0
    levels = _levels(entry)

    if contract:
        strike = int(_float(_get(contract, "strike", 0)))
        option_type = _text(
            _get(contract, "option_type", "CE" if side == "CALL" else "PE"),
            "CE" if side == "CALL" else "PE",
        )
        instrument = f"{strike} {option_type}" if strike > 0 else "NOT_SELECTED"
    else:
        instrument = "NOT_SELECTED"
        if side in {"CALL", "PUT"}:
            blockers.append(f"No usable {side} contract found")

    action = "NO_TRADE"
    entry_mode = "WAIT"

    if not blockers:
        action = "BUY_CALL" if side == "CALL" else "BUY_PUT"
        entry_mode = "WAIT_FOR_PREMIUM_TRIGGER"

    return Decision(
        action=action,
        instrument=instrument,
        conviction=round(confidence, 2),
        side=side,
        entry_mode=entry_mode,
        strike_label=label,
        entry_reference=round(entry, 2),
        stop_loss=levels["sl"],
        target_1=levels["t1"],
        target_2=levels["t2"],
        target_3=levels["t3"],
        reasons=reasons,
        blockers=blockers,
    )
