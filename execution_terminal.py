from cockpit_common import *
N={"NSE:NIFTY50-INDEX":"NIFTY","NSE:NIFTYBANK-INDEX":"BANKNIFTY","BSE:SENSEX-INDEX":"SENSEX"}
def g(d,k,x="UNKNOWN"):return d.get(k,x) if isinstance(d,dict) else x
def main():
    while True:
        s=state();clear();print("="*94);print("COMMANDER — EXECUTION DESK".center(94));print("="*94);print(f"UPDATED {age_text(s)}")
        for sym,name in N.items():
            c=s.get("contexts",{}).get(sym,{});d=c.get("decision") or {};l=c.get("lifecycle") or {};e=c.get("evidence") or {};b=c.get("battle") or {}
            print("\n"+f" {name} ".center(94,"-"));print(f"ACTION {g(d,'action','NO_DATA'):<14} INSTRUMENT {g(d,'instrument','-'):<14} CONF {f(g(d,'conviction',0)):>6.2f}%");print(f"ENTRY ₹{f(g(d,'entry_trigger',g(d,'entry_reference',0))):.2f} | SL ₹{f(g(d,'stop_loss',0)):.2f} | T1 ₹{f(g(d,'target_1',0)):.2f} | T2 ₹{f(g(d,'target_2',0)):.2f} | T3 ₹{f(g(d,'target_3',0)):.2f}");print(f"BATTLE {g(b,'commander_status',g(b,'status','UNKNOWN'))} | EVIDENCE {g(e,'verdict','NO_BIAS')} | FLOW {g(c.get('flow') or {},'dominant_side','BALANCED')}");print(f"LIFECYCLE {g(l,'state','NO_DATA')} | {g(l,'action','WAIT')} | P&L {f(g(l,'pnl_points',0)):+.2f} ({f(g(l,'pnl_percent',0)):+.2f}%)");bl=g(d,'blockers',[]) or []
            if bl:print("BLOCKERS: "+" | ".join(map(str,bl[:3])))
        time.sleep(TERMINAL_REFRESH_SECONDS)
if __name__=="__main__":main()
