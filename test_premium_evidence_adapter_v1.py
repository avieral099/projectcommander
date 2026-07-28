from premium_evidence_adapter import normalise_premium_evidence

row = {
    "timestamp": "2026-07-28T15:29:00+05:30",
    "index_symbol": "NSE:NIFTY50-INDEX",
    "spot_price": 23987.05,
    "atm_straddle": 14.20,
    "premium_flow_side": "CALL",
    "premium_score": 78,
    "commander_state": "ROTATION_WITH_EXPANSION",
    "decay_state": "PREMIUM_EXPANSION",
    "rotation_state": "DOWNWARD_ROTATION",
    "straddle_structure": "DECAY_BREAKDOWN_UNCONFIRMED",
}

result = normalise_premium_evidence(row, source="test")

assert result["premium_flow_side"] == "CALL"
assert result["premium_score"] == 78
assert result["status"] == "CONNECTED"
assert result["missing_fields"] == []

partial = normalise_premium_evidence(
    {"timestamp": "2026-07-28T10:00:00"},
    source="test",
)
assert partial["status"] == "PARTIAL"
assert partial["missing_fields"]

print("ALL PREMIUM EVIDENCE ADAPTER V1 TESTS PASSED")
print(
    f"CONNECTED={result['premium_flow_side']}:{result['premium_score']} "
    f"PARTIAL_MISSING={partial['missing_fields']}"
)
