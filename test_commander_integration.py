from commander_context import CommanderContext
from commander_terminal import (
    print_commander_context,
)


class Dummy:
    pass


context = CommanderContext(
    symbol="NSE:NIFTY50-INDEX"
)

context.recorder_result = {
    "status": "RECORDED",
    "contracts_inserted": 14,
    "straddles_inserted": 7,
}

context.behaviour = Dummy()
context.behaviour.regime = (
    "PREMIUM_MIGRATION_DAY"
)
context.behaviour.commander_view = (
    "TRACK LEADING STRIKE"
)

context.flow = Dummy()
context.flow.dominant_side = "CALL"
context.flow.call_leader_display = (
    "OTM1 CALL — 25200 CE"
)
context.flow.put_leader_display = (
    "ATM PUT — 25100 PE"
)
context.flow.atm_erosion_destination = (
    "ATM CALL 25100 CE → "
    "OTM1 CALL — 25200 CE"
)

context.structure = Dummy()
context.structure.structure_state = (
    "EXPANSION_BREAKOUT"
)
context.structure.straddle_bias = (
    "LONG_STRADDLE"
)
context.structure.short_straddle_stance = (
    "AVOID"
)

context.battle = Dummy()
context.battle.zone = "EXPANSION_ZONE"
context.battle.commander_status = "ATTACK"
context.battle.battle_score = 7

context.evidence = Dummy()
context.evidence.score = 85
context.evidence.verdict = (
    "HIGH_CONFIDENCE"
)
context.evidence.agreement = 5

assert context.ready is True
assert (
    context.flow.call_leader_display
    == "OTM1 CALL — 25200 CE"
)

print_commander_context(
    context
)

print(
    "ALL COMMANDER INTEGRATION V1 "
    "TESTS PASSED"
)
