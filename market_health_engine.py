from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Any

def _pct(value: Any, total: int) -> float:
    return 0.0 if total <= 0 else max(0.0, min(100.0, float(value or 0) / total * 100.0))

def analyse_market_health(snapshot: dict[str, Any]) -> dict[str, Any]:
    b = snapshot.get("breadth_5m", {})
    total = int(b.get("total", 0) or 0)
    if total <= 0:
        raise ValueError("Snapshot has no completed breadth rows")

    ema5 = _pct(b.get("above_ema5"), total)
    ema20 = _pct(b.get("above_ema20"), total)
    ema50 = _pct(b.get("above_ema50"), total)
    ema100 = _pct(b.get("above_ema100"), total)
    ema200 = _pct(b.get("above_ema200"), total)
    vwap = _pct(b.get("above_vwap"), total)
    pdc = _pct(b.get("above_pdc"), total)
    pdh = _pct(b.get("above_pdh"), total)
    pdl_down = _pct(b.get("below_pdl"), total)
    bull_stack = _pct(b.get("bullish_stack"), total)
    bear_stack = _pct(b.get("bearish_stack"), total)
    transition = _pct(b.get("transition"), total)

    raw_bull = (
        ema5*0.10 + ema20*0.15 + ema50*0.10 + ema100*0.05 + ema200*0.05 +
        vwap*0.20 + pdc*0.15 + pdh*0.05 + bull_stack*0.15
    )
    raw_bear = (
        (100-ema5)*0.10 + (100-ema20)*0.15 + (100-ema50)*0.10 +
        (100-ema100)*0.05 + (100-ema200)*0.05 + (100-vwap)*0.20 +
        (100-pdc)*0.15 + pdl_down*0.05 + bear_stack*0.15
    )
    combined = raw_bull + raw_bear
    bull = 50.0 if combined <= 0 else raw_bull / combined * 100.0
    bear = 100.0 - bull

    if bull >= 70: regime = "BULLISH"
    elif bull >= 58: regime = "BULLISH_BIAS"
    elif bull <= 30: regime = "BEARISH"
    elif bull <= 42: regime = "BEARISH_BIAS"
    else: regime = "MIXED"

    participation = (ema20 + vwap + pdc) / 3.0
    breadth = "STRONG" if participation >= 65 else "MIXED" if participation >= 45 else "WEAK"

    short_term = (ema5 + ema20 + vwap) / 3.0
    medium_term = (ema50 + ema100) / 2.0
    long_term = ema200

    momentum = "IMPROVING" if short_term >= medium_term + 8 else "WEAKENING" if short_term <= medium_term - 8 else "BALANCED"
    trend = "HEALTHY" if medium_term >= 60 and long_term >= 55 else "DAMAGED" if medium_term <= 40 and long_term <= 45 else "TRANSITION"

    risk_points, warnings = 0, []
    if transition >= 65:
        risk_points += 1; warnings.append("Most stocks remain in transition.")
    if abs(ema5-ema20) >= 20:
        risk_points += 1; warnings.append("Short-term EMA breadth is internally divergent.")
    if abs(vwap-pdc) >= 20:
        risk_points += 1; warnings.append("VWAP and PDC participation disagree.")
    if pdl_down >= 20:
        risk_points += 2; warnings.append("Meaningful participation below previous-day low.")
    if bull_stack < 15 and bear_stack < 15:
        risk_points += 1; warnings.append("Directional EMA-stack conviction is limited.")
    risk = "HIGH" if risk_points >= 4 else "ELEVATED" if risk_points >= 2 else "LOW"

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "universe": snapshot.get("universe", "UNKNOWN"),
        "scanned": snapshot.get("completed_symbols", total),
        "total": snapshot.get("requested_symbols", total),
        "bull_score": round(bull, 2),
        "bear_score": round(bear, 2),
        "regime": regime,
        "breadth": breadth,
        "momentum": momentum,
        "trend": trend,
        "risk": risk,
        "participation_pct": round(participation, 2),
        "vwap_pct": round(vwap, 2),
        "pdc_pct": round(pdc, 2),
        "short_term_pct": round(short_term, 2),
        "medium_term_pct": round(medium_term, 2),
        "long_term_pct": round(long_term, 2),
        "bullish_stack_pct": round(bull_stack, 2),
        "bearish_stack_pct": round(bear_stack, 2),
        "reasons": [
            f"{ema5:.1f}% above EMA5; {ema20:.1f}% above EMA20.",
            f"{vwap:.1f}% above VWAP; {pdc:.1f}% above PDC.",
            f"{bull_stack:.1f}% bullish stacks versus {bear_stack:.1f}% bearish stacks.",
            f"{pdh:.1f}% above PDH; {pdl_down:.1f}% below PDL.",
        ],
        "warnings": warnings,
    }

def generate_market_health(snapshot_path="market_structure_snapshot.json", output_path="market_health_snapshot.json"):
    snapshot = json.loads(Path(snapshot_path).read_text())
    health = analyse_market_health(snapshot)
    Path(output_path).write_text(json.dumps(health, indent=2), encoding="utf-8")
    return health
