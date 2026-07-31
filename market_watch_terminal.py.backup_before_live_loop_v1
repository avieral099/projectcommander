from cockpit_common import *
def row(n,q):
    ch=f(q.get("chp"));st="UP" if ch>0 else "DOWN" if ch<0 else "FLAT";return f"{n:<12}{f(q.get('lp')):>11.2f}{f(q.get('ch')):>10.2f}{ch:>9.2f}%  {st}"
def main():
    while True:
        s=state();clear();print("="*74);print("COMMANDER — MARKET WATCH".center(74));print("="*74);print(f"UPDATED {age_text(s)} | PHASE {s.get('phase','UNKNOWN')}")
        print("\nINDICES / SECTORS");print(f"{'NAME':<12}{'LTP':>11}{'CHANGE':>10}{'CHANGE %':>10}  STATE");print("-"*74)
        for n,q in s.get("watchlist",{}).get("indices",{}).items():print(row(n,q))
        cash=s.get("watchlist",{}).get("cash",{});ranked=sorted(cash.items(),key=lambda x:f(x[1].get("chp")),reverse=True)
        print("\nCASH WATCHLIST");print(f"{'NAME':<12}{'LTP':>11}{'CHANGE':>10}{'CHANGE %':>10}  STATE");print("-"*74)
        for n,q in ranked:print(row(n,q))
        print("\nTOP GAINERS: "+", ".join(f"{n} {f(q.get('chp')):+.2f}%" for n,q in ranked[:3]));print("TOP LOSERS : "+", ".join(f"{n} {f(q.get('chp')):+.2f}%" for n,q in ranked[-3:][::-1]));time.sleep(TERMINAL_REFRESH_SECONDS)
if __name__=="__main__":main()
