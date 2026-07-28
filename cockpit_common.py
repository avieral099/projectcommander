import os,time
from datetime import datetime
from zoneinfo import ZoneInfo
from cockpit_config import STATE_FILE,TERMINAL_REFRESH_SECONDS
from commander_state_store import read_state
IST=ZoneInfo("Asia/Kolkata")
def clear():os.system("clear" if os.name!="nt" else "cls")
def f(v,d=0.0):
    try:return float(v)
    except (TypeError,ValueError):return d
def state():return read_state(STATE_FILE)
def age_text(s):
    x=s.get("state_written_at")
    if not x:return "NO DATA"
    try:return f"{(datetime.now(IST)-datetime.fromisoformat(x)).total_seconds():.0f}s ago"
    except:return "UNKNOWN"
