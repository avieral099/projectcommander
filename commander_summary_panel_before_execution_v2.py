from __future__ import annotations
from typing import Any

WIDTH = 92

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

def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default

def _bar(percent: float, width: int = 24) -> str:
    percent = max(0.0, min(_safe_float(percent), 100.0))
    filled = round((percent / 100.0) * width)
    return "█" * filled + "░" * (width - filled)

def print_commander_summary(context: Any, width: int = WIDTH) -> None:
    behaviour = _get(context, "behaviour", {})
    flow = _get(context, "flow", {})
    structure = _get(context, "structure", {})
    battle = _get(context, "battle", {})
    evidence = _get(context, "evidence", {})
    decision = _get(context, "decision", None)

    battle_zone = str(_get(battle, "battle_zone", _get(battle, "zone", "UNKNOWN"))).upper()
    battle_status = str(_get(battle, "commander_status", _get(battle, "status", "UNKNOWN"))).upper()
    battle_score = _safe_float(_get(battle, "battle_score", _get(battle, "score", 0.0)))
    premium_regime = str(_get(behaviour, "regime", "UNKNOWN")).upper()
    premium_flow = str(_get(flow, "dominant_side", "BALANCED")).upper()
    rotation = str(_get(flow, "rotation_state", "UNKNOWN")).upper()
    decay = str(_get(behaviour, "decay_state", _get(behaviour, "decay_status", "UNKNOWN"))).upper()
    structure_state = str(_get(structure, "structure_state", "UNKNOWN")).upper()
    straddle_bias = str(_get(structure, "straddle_bias", "NEUTRAL")).upper()
    verdict = str(_get(evidence, "verdict", "NO_BIAS")).upper()
    call_confidence = _safe_float(_get(evidence, "call_confidence", 0.0))
    put_confidence = _safe_float(_get(evidence, "put_confidence", 0.0))
    agreement = _safe_int(_get(evidence, "agreement", 0))
    score = max(call_confidence, put_confidence)
    final_action = str(_get(decision, "action", verdict)).upper()
    instrument = str(_get(decision, "instrument", "NOT_SELECTED")).upper()

    print("\n" + "=" * width)
    print("COMMANDER — LIVE CONSENSUS".center(width))
    print("=" * width)
    print("BATTLE")
    print("-" * width)
    print(f"ZONE                      : {battle_zone}")
    print(f"STATUS                    : {battle_status}")
    print(f"SCORE                     : {battle_score:.2f}")
    print("\nPREMIUM")
    print("-" * width)
    print(f"REGIME                    : {premium_regime}")
    print(f"FLOW                      : {premium_flow}")
    print(f"ROTATION                  : {rotation}")
    print(f"DECAY                     : {decay}")
    print("\nSTRADDLE")
    print("-" * width)
    print(f"STRUCTURE                 : {structure_state}")
    print(f"BIAS                      : {straddle_bias}")
    print("\nEVIDENCE")
    print("-" * width)
    print(f"CALL                      : {_bar(call_confidence)} {call_confidence:>6.2f}%")
    print(f"PUT                       : {_bar(put_confidence)} {put_confidence:>6.2f}%")
    print(f"VERDICT                   : {verdict}")
    print(f"ENGINE AGREEMENT          : {agreement}")
    print("\nFINAL ORDER")
    print("-" * width)
    print(f"ACTION                    : {final_action}")
    print(f"INSTRUMENT                : {instrument}")
    print(f"CONVICTION                : {score:.2f}%")
    print("=" * width)
