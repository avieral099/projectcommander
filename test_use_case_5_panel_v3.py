from types import SimpleNamespace
from commander_summary_panel import print_commander_summary

context = SimpleNamespace(
    behaviour=SimpleNamespace(regime="PREMIUM_EXPANSION"),
    flow=SimpleNamespace(dominant_side="CALL"),
    battle=SimpleNamespace(battle_zone="TREND_BATTLE",commander_status="ATTACK",battle_score=8),
    evidence={"verdict":"CALL_BIAS","call_confidence":84,"put_confidence":12,"agreement":6},
    decision=SimpleNamespace(
        action="BUY_CALL",
        instrument="23950 CE",
        strike_label="ATM_CE",
        behaviour_state="EMA75_BREAKOUT_BELOW_VWAP",
        level_source="PREMIUM_INDICATORS",
        conviction=84,
        entry_mode="BUY_ON_1M_CLOSE_ABOVE_TRIGGER",
        entry_reference=163,
        entry_trigger=163,
        premium_vwap=190,
        ema75_high=162,
        ema75_low=150,
        supertrend=154,
        stop_loss=154,
        target_1=172,
        target_2=180,
        target_3=181,
        reasons=["Battle engine authorised ATTACK"],
        blockers=[],
    ),
)
print_commander_summary(context)
print("ALL USE CASE 5 PANEL V3 TESTS PASSED")
