
from battle_engine import evaluate
r=evaluate(
 above_pdc=True,
 above_vwap=True,
 above_ema75=True,
 opening_range_break="UP",
 premium_flow="CALL",
 straddle_structure="LONG_STRADDLE",
)
assert r.commander_status=="ATTACK"
assert r.zone=="EXPANSION_ZONE"
print("ALL BATTLE ENGINE V1 TESTS PASSED")
