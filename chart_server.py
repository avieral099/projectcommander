import fcntl
import os
from pathlib import Path
import html,sqlite3
from http.server import BaseHTTPRequestHandler,HTTPServer
from urllib.parse import urlparse,parse_qs
DB="premium_intelligence_1m.db";IDX={"NIFTY":"NSE:NIFTY50-INDEX","BANKNIFTY":"NSE:NIFTYBANK-INDEX","SENSEX":"BSE:SENSEX-INDEX"}


CHART_SERVER_LOCK = Path(".chart_server.lock")

def acquire_chart_server_lock():
    handle = CHART_SERVER_LOCK.open("w")
    try:
        fcntl.flock(
            handle.fileno(),
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )
    except BlockingIOError:
        handle.close()
        raise RuntimeError(
            "Chart Server already running; second instance refused"
        )

    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    return handle

def series(sym):
    con=sqlite3.connect(DB);con.row_factory=sqlite3.Row;r=con.execute("SELECT timestamp,spot_price,atm_straddle FROM intelligence_summaries WHERE index_symbol=? ORDER BY timestamp DESC LIMIT 120",(sym,)).fetchall();con.close();return [dict(x) for x in reversed(r)]
def poly(v,w=900,h=260,p=25):
    if not v:return ""
    lo,hi=min(v),max(v);sp=hi-lo or 1;return " ".join(f"{p+(w-2*p)*(i/max(len(v)-1,1)):.1f},{h-p-(h-2*p)*(x-lo)/sp:.1f}" for i,x in enumerate(v))
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q=parse_qs(urlparse(self.path).query);n=q.get("index",["NIFTY"])[0].upper();data=series(IDX.get(n,IDX["NIFTY"]));spot=[x["spot_price"] for x in data];st=[x["atm_straddle"] for x in data];body=f'''<!doctype html><html><head><meta http-equiv="refresh" content="5"><style>body{{background:#0b0f14;color:#e6edf3;font-family:monospace;margin:24px}}.c{{border:1px solid #30363d;padding:16px;margin:12px 0}}svg{{background:#111820;width:100%;max-width:950px}}a{{color:#58a6ff;margin-right:20px}}</style></head><body><h1>COMMANDER CHART DESK — {html.escape(n)}</h1><p><a href="/?index=NIFTY">NIFTY</a><a href="/?index=BANKNIFTY">BANKNIFTY</a><a href="/?index=SENSEX">SENSEX</a></p><div class="c"><h2>Spot</h2><svg viewBox="0 0 900 260"><polyline fill="none" stroke="currentColor" stroke-width="2" points="{poly(spot)}"/></svg></div><div class="c"><h2>ATM Straddle</h2><svg viewBox="0 0 900 260"><polyline fill="none" stroke="currentColor" stroke-width="2" points="{poly(st)}"/></svg></div></body></html>''';raw=body.encode();self.send_response(200);self.send_header("Content-Type","text/html");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
    def log_message(self,*a):pass
if __name__=="__main__":
    chart_server_lock_handle = acquire_chart_server_lock()
    print("http://127.0.0.1:8765")
    HTTPServer(("127.0.0.1",8765),H).serve_forever()
