import argparse,sqlite3,time,os
from cockpit_config import OPTION_INDEXES,TERMINAL_REFRESH_SECONDS
DB="premium_intelligence_1m.db"
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--index",choices=["1","2","3"],default="1");a=ap.parse_args();name,symbol=OPTION_INDEXES[a.index]
    while True:
        os.system("clear");print("="*100);print(f"COMMANDER — OPTIONS / STRADDLE — {name}".center(100));print("="*100)
        try:
            con=sqlite3.connect(DB);con.row_factory=sqlite3.Row;s=con.execute("SELECT * FROM intelligence_summaries WHERE index_symbol=? ORDER BY timestamp DESC LIMIT 1",(symbol,)).fetchone();rows=[]
            if s:rows=con.execute("SELECT ladder_label,strike,option_type,ltp,bid,ask,oi,volume,iv FROM option_minute_bars WHERE timestamp=? AND index_symbol=? ORDER BY strike,option_type",(s['timestamp'],symbol)).fetchall()
            locks=con.execute("SELECT reference_type,straddle FROM reference_locks WHERE index_symbol=? ORDER BY lock_time DESC LIMIT 2",(symbol,)).fetchall();con.close()
            if not s:print("NO OPTION DATA YET")
            else:
                print(f"TIME {s['timestamp']} | SPOT {s['spot_price']:.2f} | ATM {s['atm_strike']} | STRADDLE ₹{s['atm_straddle']:.2f}");print(f"DECAY {s['decay_state']} | ROTATION {s['rotation_state']} | COMMANDER {s['commander_state']}");print("LOCKS: "+" | ".join(f"{r['reference_type']} ₹{r['straddle']:.2f}" for r in locks));print("-"*100);print(f"{'LABEL':<11}{'STRIKE':>8}{'TYPE':>6}{'LTP':>10}{'BID':>10}{'ASK':>10}{'OI':>13}{'VOL':>13}{'IV':>8}")
                for r in rows:print(f"{r['ladder_label']:<11}{r['strike']:>8}{r['option_type']:>6}{r['ltp']:>10.2f}{r['bid']:>10.2f}{r['ask']:>10.2f}{r['oi']:>13}{r['volume']:>13}{r['iv']:>8.2f}")
        except Exception as e:print(f"DB ERROR: {e}")
        time.sleep(TERMINAL_REFRESH_SECONDS)
if __name__=="__main__":main()
