from __future__ import annotations

from commander_decision_engine import analyse_decision


health = {
    "generated_at": "2026-07-29T00:41:01",
    "universe": "NIFTY50",
    "scanned": 49,
    "total": 49,
    "bull_score": 59.95,
    "bear_score": 40.05,
    "regime": "BULLISH_BIAS",
    "breadth": "MIXED",
    "momentum": "BALANCED",
    "trend": "HEALTHY",
    "risk": "HIGH",
    "participation_pct": 57.82,
    "vwap_pct": 57.14,
    "pdc_pct": 59.18,
    "bullish_stack_pct": 14.29,
    "bearish_stack_pct": 8.16,
    "warnings": [
        "Most stocks remain in transition.",
        "Meaningful participation below previous-day low.",
    ],
}

decision = analyse_decision(health)

assert decision["execution_allowed"] is False
assert decision["market_action"] == "OBSERVE_ONLY"
assert decision["risk"] == "HIGH"
assert 0 <= decision["confidence"] <= 100
assert decision["quality"] in {"A+", "A", "B", "C", "NO_TRADE"}
assert decision["blockers"]

print("ALL COMMANDER DECISION V1 TESTS PASSED")
print(
    f"ACTION={decision['market_action']} "
    f"CONFIDENCE={decision['confidence']} "
    f"QUALITY={decision['quality']}"
)
