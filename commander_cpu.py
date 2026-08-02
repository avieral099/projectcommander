from __future__ import annotations
import argparse,contextlib,fcntl,os,time,traceback
from datetime import datetime,time as clock_time
from pathlib import Path
from zoneinfo import ZoneInfo
import dashboard
from cockpit_config import CASH_WATCHLIST,CPU_LOG_FILE,INDEX_WATCHLIST,STATE_FILE
from commander_state_store import context_to_dict,serialise,write_state
from live_cache import refresh_live_cache
from event_queue import EventQueue
from commander_intelligence_engine import build_intelligence_packet
from commander_market_narrative import build_market_narrative
IST=ZoneInfo("Asia/Kolkata"); MARKET_OPEN=clock_time(9,15); MARKET_CLOSE=clock_time(15,30)

COMMANDER_CPU_LOCK = Path(".commander_cpu.lock")


def acquire_singleton_lock():
    handle = COMMANDER_CPU_LOCK.open("w")

    try:
        fcntl.flock(
            handle.fileno(),
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )
    except BlockingIOError:
        handle.close()
        raise RuntimeError(
            "Commander CPU already running; "
            "second instance refused"
        )

    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    return handle

def now():return datetime.now(IST)
def collect_watchlist():
    symbols=list(dict.fromkeys([*INDEX_WATCHLIST.values(),*CASH_WATCHLIST.values()])); q=refresh_live_cache(symbols,force=True)
    return {"indices":{n:{"symbol":s,**serialise(q.get(s,{}))} for n,s in INDEX_WATCHLIST.items()},"cash":{n:{"symbol":s,**serialise(q.get(s,{}))} for n,s in CASH_WATCHLIST.items()}}
def cycle():
    log=Path(CPU_LOG_FILE)
    with log.open("a") as fh,contextlib.redirect_stdout(fh),contextlib.redirect_stderr(fh): state=dashboard.main()
    if not isinstance(state,dict):raise RuntimeError("Run install_cockpit_v1.py first")
    with EventQueue("premium_intelligence_1m.db") as event_queue:
        event_queue_summary = event_queue.summary()
        actionable_events = event_queue.latest_actionable(
            limit=20,
            minimum_priority=2,
        )

    intelligence_packet = build_intelligence_packet(
        actionable_events
    )

    market_narrative = build_market_narrative(
        intelligence_packet
    )

    payload={"generated_at":state.get("generated_at"),"phase":state.get("phase"),"market_snapshots":serialise(state.get("market_snapshots",{})),"premium_snapshots":serialise(state.get("premium_snapshots",{})),"drivers":serialise(state.get("drivers",{})),"contexts":{k:context_to_dict(v) for k,v in state.get("commander_contexts",{}).items()},"system_statuses":serialise(state.get("system_statuses",{})),"watchlist":collect_watchlist(),"event_queue_summary":serialise(event_queue_summary),"actionable_events":serialise(actionable_events),"intelligence_packet":serialise(intelligence_packet),"market_narrative":serialise(market_narrative)}
    payload["timestamp"]=payload.get("generated_at") or now().isoformat()
    payload["updated_at"]=now().isoformat()
    payload["age_seconds"]=0
    write_state(STATE_FILE,payload);return payload
def main():
    lock_handle = acquire_singleton_lock()
    ap=argparse.ArgumentParser();ap.add_argument("--once",action="store_true");ap.add_argument("--allow-closed",action="store_true");a=ap.parse_args();print("COMMANDER CPU — SILENT BACKEND")
    while True:
        t=now();tm=t.time().replace(tzinfo=None)
        if not a.allow_closed and tm>=MARKET_CLOSE:print("CPU STOPPED — MARKET CLOSED");break
        if a.allow_closed or tm>=MARKET_OPEN:
            try:p=cycle();print(f"CPU {t:%H:%M:%S} | UPDATED | {p.get('phase')}")
            except Exception as e:
                with Path(CPU_LOG_FILE).open("a") as fh:traceback.print_exc(file=fh)
                print(f"CPU ERROR: {e}")
        else:print(f"CPU {t:%H:%M:%S} | WAITING FOR 09:15")
        if a.once:break
        time.sleep(max(1,60-now().second))
if __name__=="__main__":main()
