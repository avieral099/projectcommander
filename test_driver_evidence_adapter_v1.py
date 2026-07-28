from driver_evidence_adapter import normalise_driver_evidence

raw = {
    "drivers": [
        {"symbol": "RELIANCE", "driver_side": "BULL", "driver_score": 82},
        {"symbol": "HDFCBANK", "driver_side": "BULL", "driver_score": 78},
        {"symbol": "ICICIBANK", "driver_side": "BULL", "driver_score": 76},
        {"symbol": "INFY", "driver_side": "BULL", "driver_score": 72},
        {"symbol": "TCS", "driver_side": "BEAR", "driver_score": 68},
        {"symbol": "NIFTYIT", "driver_side": "NEUTRAL", "driver_score": 50},
    ]
}

result = normalise_driver_evidence(raw, source="test")

assert result["status"] == "CONNECTED"
assert result["driver_side"] == "BULL"
assert result["driver_state"] in {"ALIGNED", "STRONGLY_ALIGNED", "MIXED"}
assert result["participation"]["total"] == 6
assert result["leaders"]
assert result["laggards"]

partial = normalise_driver_evidence({}, source="test")
assert partial["status"] == "PARTIAL"
assert partial["missing_fields"]

print("ALL DRIVER EVIDENCE ADAPTER V1 TESTS PASSED")
print(
    f"SIDE={result['driver_side']} SCORE={result['driver_score']} "
    f"AGREEMENT={result['agreement_pct']} "
    f"PARTIAL={partial['missing_fields']}"
)
