from __future__ import annotations
import argparse, os, time
from market_health_engine import generate_market_health

WIDTH = 96

def render(h):
    os.system("clear")
    print("="*WIDTH)
    print("COMMANDER — MARKET HEALTH".center(WIDTH))
    print("="*WIDTH)
    print(f"UPDATED {h['generated_at']} | UNIVERSE {h['universe']} | SCANNED {h['scanned']}/{h['total']}")
    print("-"*WIDTH)
    print(f"REGIME {h['regime']:<18} BREADTH {h['breadth']:<10} RISK {h['risk']}")
    print(f"MOMENTUM {h['momentum']:<16} TREND {h['trend']}")
    print("-"*WIDTH)
    print(f"BULL SCORE {h['bull_score']:>6.2f}/100   BEAR SCORE {h['bear_score']:>6.2f}/100")
    print(f"PARTICIPATION {h['participation_pct']:>6.2f}%   VWAP {h['vwap_pct']:>6.2f}%   PDC {h['pdc_pct']:>6.2f}%")
    print(f"SHORT {h['short_term_pct']:>6.2f}%   MEDIUM {h['medium_term_pct']:>6.2f}%   LONG {h['long_term_pct']:>6.2f}%")
    print(f"BULL STACK {h['bullish_stack_pct']:>6.2f}%   BEAR STACK {h['bearish_stack_pct']:>6.2f}%")
    print("\nWHY\n"+"-"*WIDTH)
    for x in h["reasons"]: print("- "+x)
    print("\nWARNINGS\n"+"-"*WIDTH)
    if h["warnings"]:
        for x in h["warnings"]: print("- "+x)
    else:
        print("No structural warning detected.")
    print("="*WIDTH)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot", default="market_structure_snapshot.json")
    p.add_argument("--output", default="market_health_snapshot.json")
    p.add_argument("--refresh", type=int, default=5)
    p.add_argument("--once", action="store_true")
    a=p.parse_args()
    while True:
        try: render(generate_market_health(a.snapshot,a.output))
        except Exception as e:
            os.system("clear"); print("MARKET HEALTH ERROR:", e)
        if a.once: break
        time.sleep(max(a.refresh,1))

if __name__=="__main__": main()
