from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")


def _get(
    obj: Any,
    name: str,
    default: Any = None,
) -> Any:
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(name, default)

    return getattr(obj, name, default)


def _float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _text(
    value: Any,
    default: str = "UNKNOWN",
) -> str:
    return str(
        value if value is not None else default
    ).strip().upper()


def _timestamp(
    context: Any,
) -> str:
    recorder = _get(
        context,
        "recorder_result",
        {},
    ) or {}

    value = _get(
        recorder,
        "timestamp",
        None,
    )

    if value:
        parsed = datetime.fromisoformat(
            str(value)
        )
    else:
        parsed = datetime.now(IST)

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=IST
        )
    else:
        parsed = parsed.astimezone(
            IST
        )

    return parsed.replace(
        second=0,
        microsecond=0,
    ).isoformat()


def _observation(
    *,
    timestamp: str,
    symbol: str,
    source: str,
    location: str,
    title: str,
    direction: str,
    value: float = 0.0,
    unit: str = "",
    detail: str = "",
) -> Dict[str, Any]:
    return {
        "timestamp": timestamp,
        "index_symbol": symbol,
        "source": source,
        "location": location,
        "title": title,
        "direction": direction,
        "value": round(
            value,
            2,
        ),
        "unit": unit,
        "detail": detail,
    }


def observe(
    context: Any,
    *,
    market_snapshot: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    timestamp = _timestamp(
        context
    )

    symbol = _text(
        _get(
            context,
            "symbol",
            "UNKNOWN",
        )
    )

    snapshot = _get(
        context,
        "snapshot",
        {},
    ) or {}

    behaviour = _get(
        context,
        "behaviour",
        {},
    ) or {}

    flow = _get(
        context,
        "flow",
        {},
    ) or {}

    structure = _get(
        context,
        "structure",
        {},
    ) or {}

    market = market_snapshot or {}

    observations: List[
        Dict[str, Any]
    ] = []

    straddle = _float(
        snapshot.get(
            "atm_straddle"
        )
    )

    change_1m_pct = _float(
        _get(
            behaviour,
            "change_1m_pct",
            0.0,
        )
    )

    if change_1m_pct > 0:
        observations.append(
            _observation(
                timestamp=timestamp,
                symbol=symbol,
                source="STRADDLE",
                location="ATM_STRADDLE",
                title="ATM straddle moved higher",
                direction="UP",
                value=change_1m_pct,
                unit="%",
                detail=(
                    f"Current combined premium "
                    f"₹{straddle:.2f}"
                ),
            )
        )

    elif change_1m_pct < 0:
        observations.append(
            _observation(
                timestamp=timestamp,
                symbol=symbol,
                source="STRADDLE",
                location="ATM_STRADDLE",
                title="ATM straddle moved lower",
                direction="DOWN",
                value=abs(
                    change_1m_pct
                ),
                unit="%",
                detail=(
                    f"Current combined premium "
                    f"₹{straddle:.2f}"
                ),
            )
        )

    dominant_side = _text(
        _get(
            flow,
            "dominant_side",
            "BALANCED",
        ),
        "BALANCED",
    )

    if dominant_side in {
        "CALL",
        "PUT",
    }:
        observations.append(
            _observation(
                timestamp=timestamp,
                symbol=symbol,
                source="PREMIUM_FLOW",
                location="PREMIUM_FLOW",
                title=(
                    f"{dominant_side} premiums "
                    f"show stronger participation"
                ),
                direction=dominant_side,
                detail=(
                    "Premium flow is currently "
                    f"tilted toward {dominant_side}"
                ),
            )
        )

    structure_state = _text(
        _get(
            structure,
            "structure_state",
            "UNKNOWN",
        )
    )

    if structure_state not in {
        "UNKNOWN",
        "OPENING_RANGE_NOT_READY",
    }:
        observations.append(
            _observation(
                timestamp=timestamp,
                symbol=symbol,
                source="STRADDLE_STRUCTURE",
                location="ATM_STRADDLE",
                title="Straddle structure changed",
                direction="NEUTRAL",
                detail=structure_state,
            )
        )

    vwap_state = _text(
        market.get(
            "vwap_state",
            "UNKNOWN",
        )
    )

    if vwap_state in {
        "ABOVE_VWAP",
        "BELOW_VWAP",
    }:
        observations.append(
            _observation(
                timestamp=timestamp,
                symbol=symbol,
                source="MARKET_STRUCTURE",
                location="VWAP",
                title=(
                    "Price holding above VWAP"
                    if vwap_state == "ABOVE_VWAP"
                    else "Price holding below VWAP"
                ),
                direction=(
                    "UP"
                    if vwap_state == "ABOVE_VWAP"
                    else "DOWN"
                ),
                detail=vwap_state,
            )
        )

    supertrend_state = _text(
        market.get(
            "supertrend_state",
            "UNKNOWN",
        )
    )

    if supertrend_state in {
        "BULLISH",
        "BEARISH",
    }:
        observations.append(
            _observation(
                timestamp=timestamp,
                symbol=symbol,
                source="MARKET_STRUCTURE",
                location="SUPERTREND",
                title=(
                    "Price above Supertrend"
                    if supertrend_state == "BULLISH"
                    else "Price below Supertrend"
                ),
                direction=(
                    "UP"
                    if supertrend_state == "BULLISH"
                    else "DOWN"
                ),
                detail=supertrend_state,
            )
        )

    behaviour_report = (
        behaviour.to_dict()
        if hasattr(behaviour, "to_dict")
        else behaviour
    )

    observations.extend(
        build_premium_behaviour_observations(
            timestamp=timestamp,
            symbol=symbol,
            report=behaviour_report,
        )
    )

    return observations


def build_premium_behaviour_observations(
    *,
    timestamp: str,
    symbol: str,
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []

    if not isinstance(report, dict):
        return observations

    if report.get("status") == "UNAVAILABLE":
        return observations

    regime = _text(
        report.get("regime"),
        "UNKNOWN",
    ).upper()

    theta_state = _text(
        report.get("theta_state"),
        "UNKNOWN",
    ).upper()

    gamma_state = _text(
        report.get("gamma_state"),
        "UNKNOWN",
    ).upper()

    rotation_state = _text(
        report.get("rotation_state"),
        "UNKNOWN",
    ).upper()

    migration_state = _text(
        report.get("migration_state"),
        "UNKNOWN",
    ).upper()

    time_pass_state = _text(
        report.get("time_pass_state"),
        "UNKNOWN",
    ).upper()

    commander_view = _text(
        report.get("commander_view"),
        "",
    )

    metrics = report.get("metrics") or {}
    atm_straddle = _float(
        metrics.get("atm_straddle")
    )

    regime_direction = "NEUTRAL"

    if regime in {
        "GAMMA_EXPANSION_DAY",
        "ROTATIONAL_GAMMA_DAY",
    }:
        regime_direction = "UP"

    elif regime in {
        "PURE_THETA_DAY",
        "PREMIUM_FROZEN",
    }:
        regime_direction = "DOWN"

    observations.append(
        _observation(
            timestamp=timestamp,
            symbol=symbol,
            source="PREMIUM_BEHAVIOUR",
            location="PREMIUM_REGIME",
            title=f"Premium regime {regime}",
            direction=regime_direction,
            value=atm_straddle,
            unit="₹",
            detail=commander_view,
        )
    )

    observations.append(
        _observation(
            timestamp=timestamp,
            symbol=symbol,
            source="PREMIUM_BEHAVIOUR",
            location="THETA",
            title=f"Theta {theta_state}",
            direction=(
                "DOWN"
                if theta_state in {"HIGH", "MODERATE"}
                else "NEUTRAL"
            ),
            value=_float(report.get("theta_score")),
            unit="score",
            detail=theta_state,
        )
    )

    observations.append(
        _observation(
            timestamp=timestamp,
            symbol=symbol,
            source="PREMIUM_BEHAVIOUR",
            location="GAMMA",
            title=f"Gamma {gamma_state}",
            direction=(
                "UP"
                if gamma_state in {
                    "BUILDING",
                    "HIGH",
                    "EXPLOSIVE",
                }
                else "NEUTRAL"
            ),
            value=_float(report.get("gamma_score")),
            unit="score",
            detail=gamma_state,
        )
    )

    observations.append(
        _observation(
            timestamp=timestamp,
            symbol=symbol,
            source="PREMIUM_BEHAVIOUR",
            location="ROTATION",
            title=f"Rotation {rotation_state}",
            direction=(
                "UP"
                if rotation_state.endswith("_UP")
                else "DOWN"
                if rotation_state.endswith("_DOWN")
                else "NEUTRAL"
            ),
            value=_float(report.get("rotation_score")),
            unit="score",
            detail=rotation_state,
        )
    )

    observations.append(
        _observation(
            timestamp=timestamp,
            symbol=symbol,
            source="PREMIUM_BEHAVIOUR",
            location="MIGRATION",
            title=f"Migration {migration_state}",
            direction=(
                "UP"
                if migration_state.startswith("RIGHT")
                else "DOWN"
                if migration_state.startswith("LEFT")
                else "NEUTRAL"
            ),
            value=_float(report.get("migration_score")),
            unit="score",
            detail=migration_state,
        )
    )

    observations.append(
        _observation(
            timestamp=timestamp,
            symbol=symbol,
            source="PREMIUM_BEHAVIOUR",
            location="TIME_PASS",
            title=f"Time pass {time_pass_state}",
            direction=(
                "DOWN"
                if time_pass_state in {"HIGH", "MODERATE"}
                else "NEUTRAL"
            ),
            value=_float(report.get("time_pass_index")),
            unit="%",
            detail=time_pass_state,
        )
    )

    return observations
