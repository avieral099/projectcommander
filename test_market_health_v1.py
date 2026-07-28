from market_health_engine import analyse_market_health
s={"universe":"NIFTY50","completed_symbols":49,"requested_symbols":49,"breadth_5m":{"total":49,"above_ema5":33,"above_ema20":28,"above_ema50":29,"above_ema100":32,"above_ema200":31,"above_vwap":28,"above_pdc":29,"above_pdh":21,"below_pdl":16,"bullish_stack":7,"bearish_stack":4,"transition":38}}
h=analyse_market_health(s)
assert round(h["bull_score"]+h["bear_score"],2)==100.00
assert h["regime"] in {"BULLISH","BULLISH_BIAS","MIXED","BEARISH_BIAS","BEARISH"}
assert h["risk"] in {"LOW","ELEVATED","HIGH"}
print("ALL MARKET HEALTH V1 TESTS PASSED")
print(h["regime"], h["bull_score"], h["risk"])
