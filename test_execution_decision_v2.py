from types import SimpleNamespace
from decision_engine import generate_decision

context = SimpleNamespace(
    evidence={"verdict":"CALL_BIAS","call_confidence":84,"put_confidence":10},
    battle=SimpleNamespace(commander_status="ATTACK",battle_score=8),
    flow=SimpleNamespace(dominant_side="CALL"),
    structure=SimpleNamespace(
        straddle_bias="LONG_STRADDLE",
        structure_state="EXPANSION_BREAKOUT",
    ),
    behaviour=SimpleNamespace(regime="PREMIUM_EXPANSION"),
    snapshot={
        "contracts":{
            "ATM_CE":{
                "strike":23950,
                "option_type":"CE",
                "ltp":160,
                "ask":161,
            }
        }
    },
)

decision = generate_decision(context)
assert decision.action == "BUY_CALL"
assert decision.instrument == "23950 CE"
assert decision.entry_reference == 161.0
assert decision.stop_loss == 136.85
assert decision.target_1 == 193.2
assert decision.target_2 == 217.35
assert decision.target_3 == 241.5
print("ALL EXECUTION DECISION V2 TESTS PASSED")
