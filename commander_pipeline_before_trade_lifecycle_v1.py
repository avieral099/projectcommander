from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from battle_engine import evaluate as evaluate_battle
from commander_context import CommanderContext
from decision_engine import generate_decision
from evidence_engine import build_evidence_matrix
from premium_behaviour_engine import PremiumBehaviourEngineV3
from premium_engine import calculate_premium_snapshot
from premium_flow_engine import PremiumFlowEngine
from premium_intelligence_1m import (
    PremiumIntelligence1M,
    record_one_minute_snapshot,
)
from straddle_structure_engine import StraddleStructureEngine


DEFAULT_DB_PATH = "premium_intelligence_1m.db"


def _safe_get(
    obj: Any,
    name: str,
    default: Any = None,
) -> Any:
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


def _flow_direction(flow: Any) -> str:
    side = str(
        _safe_get(
            flow,
            "dominant_side",
            "BALANCED",
        )
    ).upper()
    return side if side in {"CALL", "PUT"} else "NONE"


def _opening_range_break(
    market_snapshot: Optional[Dict[str, Any]],
) -> str:
    status = str(
        (market_snapshot or {}).get(
            "or_status",
            "UNKNOWN",
        )
    ).upper()

    if status == "ABOVE_ORH":
        return "UP"
    if status == "BELOW_ORL":
        return "DOWN"
    return "NONE"


def _is_above_vwap(
    market_snapshot: Optional[Dict[str, Any]],
) -> bool:
    return str(
        (market_snapshot or {}).get(
            "vwap_state",
            "UNKNOWN",
        )
    ).upper() in {
        "ABOVE_VWAP",
        "ABOVE",
    }


def _is_above_ema75(
    market_snapshot: Optional[Dict[str, Any]],
) -> bool:
    return str(
        (market_snapshot or {}).get(
            "ema_structure",
            "UNKNOWN",
        )
    ).upper() in {
        "ABOVE_BOTH",
        "ABOVE",
    }


def _is_above_pdc(
    market_snapshot: Optional[Dict[str, Any]],
) -> bool:
    data = market_snapshot or {}

    if "above_pdc" in data:
        return bool(data.get("above_pdc"))

    ltp = _safe_float(data.get("ltp"))
    pdc = _safe_float(data.get("pdc"))

    return pdc > 0 and ltp > pdc


def _build_evidence_market_data(
    market_snapshot: Optional[Dict[str, Any]],
    spot_price: Optional[float],
) -> Dict[str, Any]:
    data = market_snapshot or {}

    return {
        "ltp": data.get(
            "ltp",
            spot_price or 0.0,
        ),
        "pdc": data.get("pdc", 0.0),
        "pdh": data.get("pdh", 0.0),
        "pdl": data.get("pdl", 0.0),
        "vwap_state": data.get(
            "vwap_state",
            "UNKNOWN",
        ),
        "ema_structure": data.get(
            "ema_structure",
            "UNKNOWN",
        ),
        "or_status": data.get(
            "or_status",
            "UNKNOWN",
        ),
    }


def _decorate_evidence_result(
    result: Dict[str, Any],
) -> Dict[str, Any]:
    verdict = str(
        result.get(
            "verdict",
            "NO_BIAS",
        )
    ).upper()

    if "CALL" in verdict:
        dominant_side = "CALL"
    elif "PUT" in verdict:
        dominant_side = "PUT"
    else:
        dominant_side = "NEUTRAL"

    rows = result.get("evidence", [])

    agreement = sum(
        1
        for row in rows
        if row.get("side") == dominant_side
    )

    result["score"] = max(
        _safe_float(result.get("call_confidence")),
        _safe_float(result.get("put_confidence")),
    )
    result["agreement"] = agreement
    result["dominant_side"] = dominant_side

    return result


def _driver_state(evidence: Any) -> str:
    summary = _safe_get(
        evidence,
        "driver_summary",
        None,
    )
    return str(
        _safe_get(
            summary,
            "state",
            "UNKNOWN",
        )
    ).upper()


def _build_persisted_context(
    *,
    market_snapshot: Optional[Dict[str, Any]],
    flow: Any,
    structure: Any,
    battle: Any,
    evidence: Any,
) -> Dict[str, Any]:
    market = market_snapshot or {}

    return {
        "pdc": _safe_float(market.get("pdc")),
        "pdh": _safe_float(market.get("pdh")),
        "pdl": _safe_float(market.get("pdl")),
        "vwap_state": str(
            market.get("vwap_state", "UNKNOWN")
        ).upper(),
        "ema_structure": str(
            market.get("ema_structure", "UNKNOWN")
        ).upper(),
        "supertrend_state": str(
            market.get("supertrend_state", "UNKNOWN")
        ).upper(),
        "or_status": str(
            market.get("or_status", "UNKNOWN")
        ).upper(),
        "driver_state": _driver_state(evidence),
        "premium_flow_side": str(
            _safe_get(
                flow,
                "dominant_side",
                "BALANCED",
            )
        ).upper(),
        "straddle_structure": str(
            _safe_get(
                structure,
                "structure_state",
                "UNKNOWN",
            )
        ).upper(),
        "straddle_bias": str(
            _safe_get(
                structure,
                "straddle_bias",
                "NEUTRAL",
            )
        ).upper(),
        "battle_zone": str(
            _safe_get(
                battle,
                "battle_zone",
                _safe_get(
                    battle,
                    "zone",
                    "UNKNOWN",
                ),
            )
        ).upper(),
        "battle_status": str(
            _safe_get(
                battle,
                "commander_status",
                _safe_get(
                    battle,
                    "status",
                    "UNKNOWN",
                ),
            )
        ).upper(),
        "battle_score": _safe_float(
            _safe_get(
                battle,
                "battle_score",
                _safe_get(
                    battle,
                    "score",
                    0.0,
                ),
            )
        ),
        "evidence_verdict": str(
            _safe_get(
                evidence,
                "verdict",
                "NO_BIAS",
            )
        ).upper(),
        "evidence_score": _safe_float(
            _safe_get(
                evidence,
                "score",
                0.0,
            )
        ),
        "call_confidence": _safe_float(
            _safe_get(
                evidence,
                "call_confidence",
                0.0,
            )
        ),
        "put_confidence": _safe_float(
            _safe_get(
                evidence,
                "put_confidence",
                0.0,
            )
        ),
        "engine_agreement": _safe_int(
            _safe_get(
                evidence,
                "agreement",
                0,
            )
        ),
    }


def _persist_pipeline_context(
    *,
    db_path: str | Path,
    recorder_result: Optional[Mapping[str, Any]],
    snapshot: Optional[Mapping[str, Any]],
    symbol: str,
    market_snapshot: Optional[Dict[str, Any]],
    flow: Any,
    structure: Any,
    battle: Any,
    evidence: Any,
) -> bool:
    if not recorder_result or not snapshot:
        return False

    timestamp = str(
        recorder_result.get("timestamp") or ""
    )
    expiry = str(
        snapshot.get("expiry_date") or "UNKNOWN"
    )

    if not timestamp:
        return False

    context = _build_persisted_context(
        market_snapshot=market_snapshot,
        flow=flow,
        structure=structure,
        battle=battle,
        evidence=evidence,
    )

    with PremiumIntelligence1M(db_path) as database:
        return database.enrich_intelligence_summary(
            timestamp=timestamp,
            index_symbol=symbol,
            expiry_date=expiry,
            context=context,
        )


def run_pipeline(
    symbol: str,
    *,
    spot_price: Optional[float] = None,
    premium_snapshot: Optional[Dict[str, Any]] = None,
    market_snapshot: Optional[Dict[str, Any]] = None,
    drivers: Optional[Dict[str, Dict[str, Any]]] = None,
    db_path: str | Path = DEFAULT_DB_PATH,
    timestamp: Optional[str] = None,
    battle_reference: Optional[Dict[str, Any]] = None,
) -> CommanderContext:
    context = CommanderContext(symbol=symbol)

    try:
        context.snapshot = (
            premium_snapshot
            if premium_snapshot is not None
            else calculate_premium_snapshot(
                symbol,
                spot_price=spot_price,
            )
        )
    except Exception as error:
        context.set_error("premium_engine", error)
        return context

    try:
        with PremiumIntelligence1M(db_path) as database:
            context.recorder_result = (
                record_one_minute_snapshot(
                    database,
                    context.snapshot,
                    index_symbol=symbol,
                    timestamp=timestamp,
                )
            )
    except Exception as error:
        context.set_error(
            "premium_intelligence",
            error,
        )
        return context

    try:
        with PremiumBehaviourEngineV3(db_path) as engine:
            context.behaviour = engine.analyse(symbol)
    except Exception as error:
        context.set_error(
            "premium_behaviour",
            error,
        )

    try:
        with PremiumFlowEngine(db_path) as engine:
            context.flow = engine.analyse(symbol)
    except Exception as error:
        context.set_error(
            "premium_flow",
            error,
        )

    try:
        with StraddleStructureEngine(db_path) as engine:
            context.structure = engine.analyse(symbol)
    except Exception as error:
        context.set_error(
            "straddle_structure",
            error,
        )

    try:
        structure_bias = str(
            _safe_get(
                context.structure,
                "straddle_bias",
                "NEUTRAL",
            )
        ).upper()

        context.battle = evaluate_battle(
            above_pdc=_is_above_pdc(
                market_snapshot
            ),
            above_vwap=_is_above_vwap(
                market_snapshot
            ),
            above_ema75=_is_above_ema75(
                market_snapshot
            ),
            opening_range_break=(
                _opening_range_break(
                    market_snapshot
                )
            ),
            premium_flow=_flow_direction(
                context.flow
            ),
            straddle_structure=structure_bias,
        )
    except Exception as error:
        context.set_error(
            "battle_engine",
            error,
        )

    try:
        evidence_result = build_evidence_matrix(
            market_data=_build_evidence_market_data(
                market_snapshot,
                spot_price,
            ),
            drivers=drivers,
            premium_snapshot=context.snapshot,
            battle_reference=battle_reference,
        )

        context.evidence = _decorate_evidence_result(
            evidence_result
        )
    except Exception as error:
        context.set_error(
            "evidence_engine",
            error,
        )

    try:
        persisted = _persist_pipeline_context(
            db_path=db_path,
            recorder_result=context.recorder_result,
            snapshot=context.snapshot,
            symbol=symbol,
            market_snapshot=market_snapshot,
            flow=context.flow,
            structure=context.structure,
            battle=context.battle,
            evidence=context.evidence,
        )

        if isinstance(context.recorder_result, dict):
            context.recorder_result[
                "pipeline_context_saved"
            ] = persisted
    except Exception as error:
        context.set_error(
            "pipeline_context_persistence",
            error,
        )


    try:
        context.decision = generate_decision(
            context
        )
    except Exception as error:
        context.set_error(
            "decision_engine",
            error,
        )

    return context
