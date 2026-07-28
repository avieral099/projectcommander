from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _load_optional(path: str | Path) -> dict[str, Any] | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        value = json.loads(p.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _first(data: dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return default


def _normalise_side(value: Any) -> str:
    text = str(value or "").upper()
    if any(token in text for token in ("CALL", "BULL", "UP")):
        return "BULL"
    if any(token in text for token in ("PUT", "BEAR", "DOWN")):
        return "BEAR"
    if any(token in text for token in ("BALANCED", "NEUTRAL", "MIXED")):
        return "NEUTRAL"
    return "UNKNOWN"


def _extract_premium(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {
            "status": "NOT_CONNECTED",
            "side": "UNKNOWN",
            "score": 0.0,
            "state": "UNKNOWN",
            "reasons": [],
        }

    side = _normalise_side(
        _first(
            data,
            (
                "premium_flow_side",
                "flow_side",
                "side",
                "premium_side",
                "evidence_verdict",
            ),
        )
    )

    state = str(
        _first(
            data,
            (
                "commander_state",
                "premium_state",
                "regime",
                "decay_state",
                "straddle_structure",
            ),
            "UNKNOWN",
        )
    ).upper()

    score = _number(
        _first(
            data,
            (
                "premium_score",
                "score",
                "confidence",
                "call_confidence",
                "put_confidence",
            ),
            0,
        )
    )

    if score <= 1:
        score *= 100

    reasons = []
    for key in (
        "premium_flow_side",
        "decay_state",
        "rotation_state",
        "straddle_structure",
        "commander_state",
    ):
        if key in data:
            reasons.append(f"{key}: {data[key]}")

    return {
        "status": "CONNECTED",
        "side": side,
        "score": max(0.0, min(100.0, score)),
        "state": state,
        "reasons": reasons,
    }


def _extract_drivers(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {
            "status": "NOT_CONNECTED",
            "side": "UNKNOWN",
            "score": 0.0,
            "state": "UNKNOWN",
            "reasons": [],
        }

    side = _normalise_side(
        _first(
            data,
            (
                "driver_side",
                "side",
                "bias",
                "evidence_verdict",
                "driver_verdict",
            ),
        )
    )

    state = str(
        _first(
            data,
            (
                "driver_state",
                "state",
                "regime",
                "driver_verdict",
            ),
            "UNKNOWN",
        )
    ).upper()

    score = _number(
        _first(
            data,
            (
                "driver_score",
                "score",
                "confidence",
                "agreement_pct",
            ),
            0,
        )
    )

    if score <= 1:
        score *= 100

    reasons = []
    for key in (
        "driver_side",
        "driver_state",
        "driver_verdict",
        "agreement_pct",
        "leaders",
        "laggards",
    ):
        if key in data:
            reasons.append(f"{key}: {data[key]}")

    return {
        "status": "CONNECTED",
        "side": side,
        "score": max(0.0, min(100.0, score)),
        "state": state,
        "reasons": reasons,
    }


def fuse_evidence(
    decision: dict[str, Any],
    market_health: dict[str, Any],
    premium: dict[str, Any] | None = None,
    drivers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    market_side = str(decision.get("directional_side", "NEUTRAL")).upper()
    market_score = _number(decision.get("confidence"), 0.0)
    risk = str(decision.get("risk", "HIGH")).upper()

    premium_evidence = _extract_premium(premium)
    driver_evidence = _extract_drivers(drivers)

    connected = {
        "market": True,
        "premium": premium_evidence["status"] == "CONNECTED",
        "drivers": driver_evidence["status"] == "CONNECTED",
    }

    weights = {"market": 0.40, "premium": 0.40, "drivers": 0.20}

    weighted_sum = market_score * weights["market"]
    used_weight = weights["market"]

    if connected["premium"]:
        weighted_sum += premium_evidence["score"] * weights["premium"]
        used_weight += weights["premium"]

    if connected["drivers"]:
        weighted_sum += driver_evidence["score"] * weights["drivers"]
        used_weight += weights["drivers"]

    combined_score = weighted_sum / used_weight if used_weight else 0.0

    sides = [market_side]
    if connected["premium"]:
        sides.append(premium_evidence["side"])
    if connected["drivers"]:
        sides.append(driver_evidence["side"])

    directional = [side for side in sides if side in {"BULL", "BEAR"}]
    bull_votes = directional.count("BULL")
    bear_votes = directional.count("BEAR")

    if bull_votes > bear_votes:
        fused_side = "BULL"
    elif bear_votes > bull_votes:
        fused_side = "BEAR"
    else:
        fused_side = "NEUTRAL"

    agreement = 0
    if fused_side in {"BULL", "BEAR"}:
        agreement = sum(1 for side in directional if side == fused_side)

    missing = [name for name, value in connected.items() if not value]

    blockers = list(decision.get("blockers", []))
    if missing:
        blockers.append("Missing evidence: " + ", ".join(missing))
    if risk == "HIGH":
        blockers.append("Risk remains HIGH.")
    if fused_side == "NEUTRAL":
        blockers.append("Evidence does not have a clear directional majority.")
    if connected["premium"] and premium_evidence["side"] not in {"UNKNOWN", market_side}:
        blockers.append("Premium evidence conflicts with market structure.")
    if connected["drivers"] and driver_evidence["side"] not in {"UNKNOWN", market_side}:
        blockers.append("Driver evidence conflicts with market structure.")

    execution_allowed = (
        not missing
        and risk != "HIGH"
        and fused_side in {"BULL", "BEAR"}
        and agreement >= 2
        and combined_score >= 70
        and not any("conflicts" in blocker.lower() for blocker in blockers)
    )

    if execution_allowed:
        context = "SETUP_ELIGIBLE_FOR_MANUAL_REVIEW"
    elif missing:
        context = "WAITING_FOR_EVIDENCE_CONNECTION"
    elif risk == "HIGH":
        context = "OBSERVE_ONLY_HIGH_RISK"
    else:
        context = "NO_CLEAR_SETUP"

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "universe": decision.get("universe", market_health.get("universe", "UNKNOWN")),
        "market": {
            "status": "CONNECTED",
            "side": market_side,
            "score": round(market_score, 2),
            "regime": decision.get("regime"),
            "risk": risk,
        },
        "premium": premium_evidence,
        "drivers": driver_evidence,
        "connected": connected,
        "missing_evidence": missing,
        "fused_side": fused_side,
        "agreement_votes": agreement,
        "combined_score": round(combined_score, 2),
        "context": context,
        "execution_allowed": execution_allowed,
        "blockers": sorted(set(blockers)),
        "note": (
            "Evidence Fusion V1 does not place orders. "
            "Execution eligibility only means the setup may be reviewed manually."
        ),
    }


def generate_fusion(
    decision_path: str | Path = "commander_decision_snapshot.json",
    health_path: str | Path = "market_health_snapshot.json",
    premium_path: str | Path = "premium_evidence_snapshot.json",
    drivers_path: str | Path = "driver_evidence_snapshot.json",
    output_path: str | Path = "commander_fused_evidence_snapshot.json",
) -> dict[str, Any]:
    decision = _load_optional(decision_path)
    health = _load_optional(health_path)

    if not decision:
        raise FileNotFoundError(f"Decision snapshot missing or invalid: {decision_path}")
    if not health:
        raise FileNotFoundError(f"Market-health snapshot missing or invalid: {health_path}")

    premium = _load_optional(premium_path)
    drivers = _load_optional(drivers_path)

    result = fuse_evidence(decision, health, premium, drivers)
    Path(output_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
