from __future__ import annotations

from typing import Any


WIDTH = 92


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


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _text(value: Any, default: str) -> str:
    return str(value if value is not None else default).upper()


def _bar(percent: float, width: int = 24) -> str:
    percent = max(0.0, min(_float(percent), 100.0))
    filled = round((percent / 100.0) * width)
    return "█" * filled + "░" * (width - filled)


def print_commander_summary(context: Any, width: int = WIDTH) -> None:
    behaviour = _get(context, "behaviour", {})
    flow = _get(context, "flow", {})
    structure = _get(context, "structure", {})
    battle = _get(context, "battle", {})
    evidence = _get(context, "evidence", {})
    decision = _get(context, "decision", None)

    battle_zone = _text(
        _get(battle, "battle_zone", _get(battle, "zone", "UNKNOWN")),
        "UNKNOWN",
    )
    battle_status = _text(
        _get(battle, "commander_status", _get(battle, "status", "UNKNOWN")),
        "UNKNOWN",
    )
    battle_score = _float(
        _get(battle, "battle_score", _get(battle, "score", 0.0))
    )
    premium_regime = _text(_get(behaviour, "regime", "UNKNOWN"), "UNKNOWN")
    premium_flow = _text(_get(flow, "dominant_side", "BALANCED"), "BALANCED")
    rotation = _text(
        _get(flow, "rotation_state", _get(behaviour, "rotation_state", "UNKNOWN")),
        "UNKNOWN",
    )
    decay = _text(
        _get(behaviour, "decay_state", _get(behaviour, "decay_status", "UNKNOWN")),
        "UNKNOWN",
    )
    structure_state = _text(
        _get(structure, "structure_state", "UNKNOWN"),
        "UNKNOWN",
    )
    straddle_bias = _text(
        _get(structure, "straddle_bias", "NEUTRAL"),
        "NEUTRAL",
    )
    verdict = _text(_get(evidence, "verdict", "NO_BIAS"), "NO_BIAS")
    call_confidence = _float(_get(evidence, "call_confidence", 0.0))
    put_confidence = _float(_get(evidence, "put_confidence", 0.0))
    agreement = _int(_get(evidence, "agreement", 0))

    action = _text(_get(decision, "action", verdict), verdict)
    instrument = _text(_get(decision, "instrument", "NOT_SELECTED"), "NOT_SELECTED")
    conviction = _float(
        _get(decision, "conviction", max(call_confidence, put_confidence))
    )
    strike_label = _text(
        _get(decision, "strike_label", "NOT_SELECTED"),
        "NOT_SELECTED",
    )
    entry_mode = _text(_get(decision, "entry_mode", "WAIT"), "WAIT")
    entry = _float(_get(decision, "entry_reference", 0.0))
    sl = _float(_get(decision, "stop_loss", 0.0))
    t1 = _float(_get(decision, "target_1", 0.0))
    t2 = _float(_get(decision, "target_2", 0.0))
    t3 = _float(_get(decision, "target_3", 0.0))
    trail = _text(
        _get(decision, "trail_reference", "SUPERTREND_OR_EMA75_LOW"),
        "SUPERTREND_OR_EMA75_LOW",
    )
    reasons = list(_get(decision, "reasons", []) or [])
    blockers = list(_get(decision, "blockers", []) or [])

    print("\n" + "=" * width)
    print("COMMANDER — EXECUTION CONSENSUS".center(width))
    print("=" * width)
    print(
        f"BATTLE                    : "
        f"{battle_status} | {battle_zone} | {battle_score:.2f}"
    )
    print(
        f"PREMIUM                   : "
        f"{premium_flow} | {premium_regime}"
    )
    print(
        f"ROTATION / DECAY          : "
        f"{rotation} | {decay}"
    )
    print(
        f"STRADDLE                  : "
        f"{structure_state} | {straddle_bias}"
    )
    print("-" * width)
    print(
        f"CALL                      : "
        f"{_bar(call_confidence)} {call_confidence:>6.2f}%"
    )
    print(
        f"PUT                       : "
        f"{_bar(put_confidence)} {put_confidence:>6.2f}%"
    )
    print(
        f"EVIDENCE                  : "
        f"{verdict} | AGREEMENT {agreement}"
    )

    print("\n" + " COMMANDER ORDER ".center(width, "-"))
    print(f"ACTION                    : {action}")
    print(f"INSTRUMENT                : {instrument}")
    print(f"STRIKE SELECTION          : {strike_label}")
    print(f"ENTRY MODE                : {entry_mode}")
    print(f"ENTRY REFERENCE           : ₹{entry:.2f}")
    print(f"STOP LOSS                 : ₹{sl:.2f}")
    print(f"TARGET 1                  : ₹{t1:.2f}")
    print(f"TARGET 2                  : ₹{t2:.2f}")
    print(f"TARGET 3                  : ₹{t3:.2f}")
    print(f"TRAIL                     : {trail}")
    print(f"CONVICTION                : {conviction:.2f}%")

    print("\n" + " WHY ".center(width, "-"))
    if reasons:
        for reason in reasons:
            print(f"✓ {reason}")
    else:
        print("• No supporting reason recorded.")

    if blockers:
        print("\n" + " BLOCKERS ".center(width, "-"))
        for blocker in blockers:
            print(f"! {blocker}")

    print("=" * width)
