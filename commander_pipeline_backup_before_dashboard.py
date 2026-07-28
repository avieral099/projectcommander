from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from battle_engine import evaluate as evaluate_battle
from commander_context import CommanderContext
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


def _flow_direction(flow: Any) -> str:
    side = str(
        _safe_get(
            flow,
            "dominant_side",
            "BALANCED",
        )
    ).upper()

    if side in {"CALL", "PUT"}:
        return side

    return "NONE"


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

    ltp = float(data.get("ltp") or 0.0)
    pdc = float(data.get("pdc") or 0.0)

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

    rows = result.get(
        "evidence",
        [],
    )

    agreement = sum(
        1
        for row in rows
        if row.get("side") == dominant_side
    )

    result["score"] = max(
        float(
            result.get(
                "call_confidence",
                0.0,
            )
            or 0.0
        ),
        float(
            result.get(
                "put_confidence",
                0.0,
            )
            or 0.0
        ),
    )
    result["agreement"] = agreement
    result["dominant_side"] = (
        dominant_side
    )

    return result


def run_pipeline(
    symbol: str,
    *,
    spot_price: Optional[float] = None,
    premium_snapshot: Optional[
        Dict[str, Any]
    ] = None,
    market_snapshot: Optional[
        Dict[str, Any]
    ] = None,
    drivers: Optional[
        Dict[str, Dict[str, Any]]
    ] = None,
    db_path: str | Path = DEFAULT_DB_PATH,
    timestamp: Optional[str] = None,
    battle_reference: Optional[
        Dict[str, Any]
    ] = None,
) -> CommanderContext:
    context = CommanderContext(
        symbol=symbol
    )

    try:
        if premium_snapshot is not None:
            context.snapshot = (
                premium_snapshot
            )
        else:
            context.snapshot = (
                calculate_premium_snapshot(
                    symbol,
                    spot_price=spot_price,
                )
            )
    except Exception as error:
        context.set_error(
            "premium_engine",
            error,
        )
        return context

    try:
        with PremiumIntelligence1M(
            db_path
        ) as database:
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
        with PremiumBehaviourEngineV3(
            db_path
        ) as engine:
            context.behaviour = (
                engine.analyse(symbol)
            )
    except Exception as error:
        context.set_error(
            "premium_behaviour",
            error,
        )

    try:
        with PremiumFlowEngine(
            db_path
        ) as engine:
            context.flow = (
                engine.analyse(symbol)
            )
    except Exception as error:
        context.set_error(
            "premium_flow",
            error,
        )

    try:
        with StraddleStructureEngine(
            db_path
        ) as engine:
            context.structure = (
                engine.analyse(symbol)
            )
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
            straddle_structure=(
                structure_bias
            ),
        )
    except Exception as error:
        context.set_error(
            "battle_engine",
            error,
        )

    try:
        evidence_result = (
            build_evidence_matrix(
                market_data=(
                    _build_evidence_market_data(
                        market_snapshot,
                        spot_price,
                    )
                ),
                drivers=drivers,
                premium_snapshot=(
                    context.snapshot
                ),
                battle_reference=(
                    battle_reference
                ),
            )
        )

        context.evidence = (
            _decorate_evidence_result(
                evidence_result
            )
        )

    except Exception as error:
        context.set_error(
            "evidence_engine",
            error,
        )

    return context
