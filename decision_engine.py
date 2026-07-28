from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass
class Decision:
    action: str
    instrument: str
    conviction: float
    side: str
    entry_mode: str = "WAIT"
    strike_label: str = "NOT_SELECTED"
    behaviour_state: str = "UNKNOWN"
    level_source: str = "UNAVAILABLE"
    entry_reference: float = 0.0
    entry_trigger: float = 0.0
    stop_loss: float = 0.0
    target_1: float = 0.0
    target_2: float = 0.0
    target_3: float = 0.0
    premium_vwap: float = 0.0
    ema75_high: float = 0.0
    ema75_low: float = 0.0
    supertrend: float = 0.0
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


def _indicator_value(contract: Any, *names: str) -> float:
    for name in names:
        value = _float(_get(contract, name, 0.0))
        if value > 0:
            return value
    return 0.0


def _premium_levels(contract: Any, entry: float) -> dict[str, Any]:
    vwap = _indicator_value(contract, "premium_vwap", "vwap")
    ema_high = _indicator_value(contract, "ema75_high", "premium_ema75_high")
    ema_low = _indicator_value(contract, "ema75_low", "premium_ema75_low")
    supertrend = _indicator_value(contract, "supertrend", "premium_supertrend")
    swing_high = _indicator_value(contract, "recent_swing_high", "swing_high")

    indicator_ready = ema_high > 0 and ema_low > 0 and supertrend > 0

    if indicator_ready:
        trigger = max(entry, ema_high)
        valid_stops = [level for level in (ema_low, supertrend) if 0 < level < trigger]
        stop = max(valid_stops) if valid_stops else round(trigger * 0.88, 2)
        risk = max(trigger - stop, trigger * 0.05)

        targets = []
        for level in (swing_high, vwap):
            if level > trigger:
                targets.append(level)

        targets.extend([
            trigger + risk,
            trigger + (2 * risk),
            trigger + (3 * risk),
        ])

        unique_targets = []
        for level in sorted(targets):
            rounded = round(level, 2)
            if rounded > trigger and rounded not in unique_targets:
                unique_targets.append(rounded)

        while len(unique_targets) < 3:
            multiplier = len(unique_targets) + 1
            unique_targets.append(round(trigger + multiplier * risk, 2))

        return {
            "source": "PREMIUM_INDICATORS",
            "trigger": round(trigger, 2),
            "stop": round(stop, 2),
            "t1": unique_targets[0],
            "t2": unique_targets[1],
            "t3": unique_targets[2],
            "vwap": vwap,
            "ema_high": ema_high,
            "ema_low": ema_low,
            "supertrend": supertrend,
        }

    return {
        "source": "PERCENTAGE_FALLBACK",
        "trigger": round(entry, 2),
        "stop": round(entry * 0.85, 2) if entry > 0 else 0.0,
        "t1": round(entry * 1.20, 2) if entry > 0 else 0.0,
        "t2": round(entry * 1.35, 2) if entry > 0 else 0.0,
        "t3": round(entry * 1.50, 2) if entry > 0 else 0.0,
        "vwap": vwap,
        "ema_high": ema_high,
        "ema_low": ema_low,
        "supertrend": supertrend,
    }


def _behaviour(entry: float, levels: Mapping[str, Any]) -> str:
    ema_high = _float(levels.get("ema_high"))
    ema_low = _float(levels.get("ema_low"))
    vwap = _float(levels.get("vwap"))
    supertrend = _float(levels.get("supertrend"))

    if not all((ema_high, ema_low, supertrend)):
        return "INDICATORS_NOT_READY"
    if entry < ema_low and entry < supertrend:
        return "PREMIUM_WEAK"
    if ema_low <= entry < ema_high and entry >= supertrend:
        return "RECOVERY_ZONE"
    if entry >= ema_high and entry >= supertrend and (vwap <= 0 or entry < vwap):
        return "EMA75_BREAKOUT_BELOW_VWAP"
    if entry >= ema_high and entry >= supertrend and vwap > 0 and entry >= vwap:
        return "STRONG_PREMIUM_EXPANSION"
    return "TRANSITION"


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
    flow_side = _text(_get(flow, "dominant_side", "BALANCED"), "BALANCED")
    straddle_bias = _text(_get(structure, "straddle_bias", "NEUTRAL"), "NEUTRAL")
    regime = _text(_get(behaviour, "regime", "UNKNOWN"), "UNKNOWN")

    reasons = []
    blockers = []

    if side == "NEUTRAL":
        blockers.append("No directional evidence bias")

    if battle_status == "ATTACK":
        reasons.append("Battle engine authorised ATTACK")
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

    if regime != "UNKNOWN":
        reasons.append(f"Premium regime: {regime}")

    label, contract = (
        _select_contract(snapshot, side, confidence)
        if side in {"CALL", "PUT"}
        else ("NOT_SELECTED", None)
    )

    entry = _contract_price(contract) if contract else 0.0
    levels = _premium_levels(contract, entry) if contract else _premium_levels({}, 0.0)
    state = _behaviour(entry, levels)

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

    if levels["source"] == "PREMIUM_INDICATORS":
        reasons.append(f"Premium behaviour: {state}")
        if state in {"PREMIUM_WEAK", "RECOVERY_ZONE", "TRANSITION"}:
            blockers.append(f"Premium trigger not confirmed: {state}")
    else:
        reasons.append("Premium indicators unavailable; fallback risk map used")

    action = "NO_TRADE"
    entry_mode = "WAIT"

    if not blockers:
        action = "BUY_CALL" if side == "CALL" else "BUY_PUT"
        entry_mode = (
            "BUY_ON_1M_CLOSE_ABOVE_TRIGGER"
            if levels["source"] == "PREMIUM_INDICATORS"
            else "WAIT_FOR_PREMIUM_TRIGGER"
        )

    return Decision(
        action=action,
        instrument=instrument,
        conviction=round(confidence, 2),
        side=side,
        entry_mode=entry_mode,
        strike_label=label,
        behaviour_state=state,
        level_source=levels["source"],
        entry_reference=round(entry, 2),
        entry_trigger=levels["trigger"],
        stop_loss=levels["stop"],
        target_1=levels["t1"],
        target_2=levels["t2"],
        target_3=levels["t3"],
        premium_vwap=round(levels["vwap"], 2),
        ema75_high=round(levels["ema_high"], 2),
        ema75_low=round(levels["ema_low"], 2),
        supertrend=round(levels["supertrend"], 2),
        reasons=reasons,
        blockers=blockers,
    )
