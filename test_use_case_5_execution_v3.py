from types import SimpleNamespace
from decision_engine import generate_decision

context = SimpleNamespace(
    evidence={"verdict":"CALL_BIAS","call_confidence":84,"put_confidence":10},
    battle=SimpleNamespace(commander_status="ATTACK",battle_score=8),
    flow=SimpleNamespace(dominant_side="CALL"),
    structure=SimpleNamespace(straddle_bias="LONG_STRADDLE"),
    behaviour=SimpleNamespace(regime="PREMIUM_EXPANSION"),
    snapshot={
        "contracts":{
            "ATM_CE":{
                "strike":23950,
                "option_type":"CE",
                "ltp":162.5,
                "ask":163,
                "premium_vwap":190,
                "ema75_high":162,
                "ema75_low":150,
                "supertrend":154,
                "recent_swing_high":180,
            }
        }
    },
)

decision = generate_decision(context)
assert decision.action == "BUY_CALL"
assert decision.instrument == "23950 CE"
assert decision.level_source == "PREMIUM_INDICATORS"
assert decision.entry_trigger == 163.0
assert decision.stop_loss == 154.0
assert decision.target_1 == 172.0
assert decision.target_2 == 180.0
assert decision.target_3 == 181.0
print("ALL USE CASE 5 EXECUTION V3 TESTS PASSED")
