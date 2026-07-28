from types import SimpleNamespace
from decision_engine import generate_decision

context = SimpleNamespace(
    evidence={"verdict":"CALL_BIAS","call_confidence":84,"put_confidence":12},
    battle=SimpleNamespace(commander_status="ATTACK"),
    flow=SimpleNamespace(dominant_side="CALL"),
    structure=SimpleNamespace(straddle_bias="LONG_STRADDLE"),
    behaviour=SimpleNamespace(regime="PREMIUM_EXPANSION"),
    snapshot={"atm_strike":23950},
)

decision = generate_decision(context)
assert decision.action == "BUY_CALL"
assert decision.instrument == "23950 CE"
assert decision.conviction == 84.0
assert not decision.blockers

wait_context = SimpleNamespace(
    evidence={"verdict":"WEAK_CALL_BIAS","call_confidence":50,"put_confidence":0},
    battle=SimpleNamespace(commander_status="WAIT"),
    flow=SimpleNamespace(dominant_side="BALANCED"),
    structure=SimpleNamespace(straddle_bias="NEUTRAL"),
    behaviour=SimpleNamespace(regime="MIXED_PREMIUM_REGIME"),
    snapshot={"atm_strike":23950},
)

wait_decision = generate_decision(wait_context)
assert wait_decision.action == "NO_TRADE"
assert wait_decision.blockers

print("ALL DECISION ENGINE V1 TESTS PASSED")
