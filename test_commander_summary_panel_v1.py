from types import SimpleNamespace
from commander_summary_panel import print_commander_summary

context = SimpleNamespace(
    behaviour=SimpleNamespace(regime="PREMIUM_EXPANSION", decay_state="BALANCED"),
    flow=SimpleNamespace(dominant_side="CALL", rotation_state="AGGRESSIVE_UPWARD_ROTATION"),
    structure=SimpleNamespace(structure_state="EXPANSION_BREAKOUT", straddle_bias="LONG_STRADDLE"),
    battle=SimpleNamespace(battle_zone="TREND_BATTLE", commander_status="ATTACK", battle_score=8),
    evidence={"verdict":"CALL_BIAS","call_confidence":84,"put_confidence":12,"agreement":6},
    decision=SimpleNamespace(action="BUY_CALL", instrument="23900 CE"),
)
print_commander_summary(context)
print("ALL COMMANDER SUMMARY PANEL V1 TESTS PASSED")
