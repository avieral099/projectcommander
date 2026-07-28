from commander_evidence_fusion import fuse_evidence

decision = {
    "universe": "NIFTY50",
    "directional_side": "BULL",
    "confidence": 72,
    "regime": "BULLISH_BIAS",
    "risk": "ELEVATED",
    "blockers": [],
}

health = {"universe": "NIFTY50"}

premium = {
    "premium_flow_side": "CALL",
    "premium_score": 78,
    "decay_state": "PREMIUM_EXPANSION",
}

drivers = {
    "driver_side": "BULL",
    "driver_score": 74,
    "driver_state": "ALIGNED",
}

result = fuse_evidence(decision, health, premium, drivers)

assert result["fused_side"] == "BULL"
assert result["agreement_votes"] == 3
assert result["combined_score"] >= 70
assert result["execution_allowed"] is True

missing = fuse_evidence(decision, health, None, None)
assert missing["execution_allowed"] is False
assert "premium" in missing["missing_evidence"]
assert "drivers" in missing["missing_evidence"]

print("ALL COMMANDER EVIDENCE FUSION V1 TESTS PASSED")
print(
    f"FULL={result['context']} SCORE={result['combined_score']} | "
    f"MISSING={missing['context']}"
)
