from __future__ import annotations
import json, sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

IST = ZoneInfo('Asia/Kolkata')
OPEN_STATES = {'ACTIVE','TARGET_1_HIT','TARGET_2_HIT'}

@dataclass
class Lifecycle:
    timestamp:str; trading_date:str; index_symbol:str; state:str; previous_state:str
    side:str; instrument:str; strike_label:str; current_price:float; entry_price:float
    stop_loss:float; target_1:float; target_2:float; target_3:float; trail_stop:float
    pnl_points:float; pnl_percent:float; action:str; reason:str
    warnings:list[str]=field(default_factory=list)

def _g(o,n,d=None):
    if o is None:return d
    return o.get(n,d) if isinstance(o,dict) else getattr(o,n,d)

def _f(v,d=0.0):
    try:return float(v)
    except (TypeError,ValueError):return d

def _t(v,d): return str(v or d).strip().upper()

def _ts(v=None):
    x=datetime.fromisoformat(v) if v else datetime.now(IST)
    x=x.replace(tzinfo=IST) if x.tzinfo is None else x.astimezone(IST)
    return x.replace(second=0,microsecond=0).isoformat()

def _identity(c):
    s=int(_f(_g(c,'strike',0))); typ=_t(_g(c,'option_type',''),'')
    return f'{s} {typ}' if s>0 and typ in {'CE','PE'} else ''

def _price(c):
    ask=_f(_g(c,'ask',0)); ltp=_f(_g(c,'ltp',0)); return ask if ask>0 else ltp

def _live_price(snapshot,instrument,label):
    contracts=_g(snapshot,'contracts',{}) or {}
    c=contracts.get(label)
    if c and _identity(c)==instrument:return _price(c)
    for c in contracts.values():
        if _identity(c)==instrument:return _price(c)
    return 0.0

class TradeLifecycleEngine:
    def __init__(self,db_path='premium_intelligence_1m.db'):
        self.connection=sqlite3.connect(Path(db_path)); self.connection.row_factory=sqlite3.Row; self._schema()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
    def close(self):self.connection.close()
    def _schema(self):
        self.connection.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS trade_lifecycle_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp TEXT NOT NULL,trading_date TEXT NOT NULL,
          index_symbol TEXT NOT NULL,state TEXT NOT NULL,previous_state TEXT NOT NULL,side TEXT NOT NULL,
          instrument TEXT NOT NULL,strike_label TEXT NOT NULL,current_price REAL NOT NULL,entry_price REAL NOT NULL,
          stop_loss REAL NOT NULL,target_1 REAL NOT NULL,target_2 REAL NOT NULL,target_3 REAL NOT NULL,
          trail_stop REAL NOT NULL,pnl_points REAL NOT NULL,pnl_percent REAL NOT NULL,action TEXT NOT NULL,
          reason TEXT NOT NULL,warnings_json TEXT NOT NULL,
          UNIQUE(timestamp,index_symbol,instrument,state));
        CREATE INDEX IF NOT EXISTS idx_lifecycle_latest ON trade_lifecycle_events(trading_date,index_symbol,id);
        '''); self.connection.commit()
    def latest(self,date,symbol):
        r=self.connection.execute('SELECT * FROM trade_lifecycle_events WHERE trading_date=? AND index_symbol=? ORDER BY id DESC LIMIT 1',(date,symbol)).fetchone()
        return dict(r) if r else None
    def _save(self,x):
        d=asdict(x); d['warnings_json']=json.dumps(d.pop('warnings'))
        cols=','.join(d); vals=','.join(':'+k for k in d)
        self.connection.execute(f'INSERT OR REPLACE INTO trade_lifecycle_events({cols}) VALUES({vals})',d); self.connection.commit()
    def evaluate(self,context,timestamp=None):
        timestamp=_ts(timestamp or _g(_g(context,'recorder_result',{}),'timestamp',None)); date=timestamp[:10]
        symbol=_t(_g(context,'symbol','UNKNOWN'),'UNKNOWN'); decision=_g(context,'decision',None); snapshot=_g(context,'snapshot',{}) or {}
        prev=self.latest(date,symbol); prev_state=_t((prev or {}).get('state','NO_TRADE'),'NO_TRADE')
        da=_t(_g(decision,'action','NO_TRADE'),'NO_TRADE'); ds=_t(_g(decision,'side','NEUTRAL'),'NEUTRAL')
        di=_t(_g(decision,'instrument','NOT_SELECTED'),'NOT_SELECTED'); label=_t(_g(decision,'strike_label','NOT_SELECTED'),'NOT_SELECTED')
        trigger=_f(_g(decision,'entry_trigger',_g(decision,'entry_reference',0))); sl=_f(_g(decision,'stop_loss',0))
        t1=_f(_g(decision,'target_1',0)); t2=_f(_g(decision,'target_2',0)); t3=_f(_g(decision,'target_3',0))
        active=bool(prev and prev_state in OPEN_STATES)
        if active:
            instrument=_t(prev['instrument'],'NOT_SELECTED'); side=_t(prev['side'],'NEUTRAL'); label=_t(prev['strike_label'],label)
            entry=_f(prev['entry_price']); sl=_f(prev['stop_loss']); t1=_f(prev['target_1']); t2=_f(prev['target_2']); t3=_f(prev['target_3']); trail=_f(prev['trail_stop'],sl)
        else:
            instrument,side,entry,trail=di,ds,trigger,sl
        current=_live_price(snapshot,instrument,label); warnings=[]
        if current<=0:
            current=_f(_g(decision,'entry_reference',0)); warnings.append('Live price unavailable; decision reference used')
        state,action,reason='NO_TRADE','WAIT','No approved trade'
        if active:
            if current<=max(sl,trail): state,action,reason='STOP_HIT','EXIT','Premium reached stop or trailing stop'
            elif t3>0 and current>=t3: state,action,reason,trail='TARGET_3_HIT','FULL_EXIT','Final target achieved',max(trail,t2)
            elif t2>0 and current>=t2: state,action,reason,trail='TARGET_2_HIT','BOOK_25_AND_TRAIL','Second target achieved',max(trail,t1)
            elif t1>0 and current>=t1: state,action,reason,trail='TARGET_1_HIT','BOOK_25_MOVE_SL_COST','First target achieved',max(trail,entry)
            elif da=='NO_TRADE': state,action,reason='EXIT_SIGNAL','EXIT','Commander consensus withdrawn'
            elif ds not in {side,'NEUTRAL'}: state,action,reason='EXIT_SIGNAL','EXIT','Opposite-side decision detected'
            else: state,action,reason='ACTIVE','HOLD','Trade active; levels intact'
        elif da in {'BUY_CALL','BUY_PUT'}:
            if trigger>0 and current>=trigger: state,action,reason='ACTIVE',da,'Entry trigger satisfied; virtual lifecycle activated'
            else: state,action,reason='PREPARE','WAIT_FOR_TRIGGER','Trade approved; premium trigger pending'
        pnl=current-entry if entry>0 else 0.0; pnlpct=(pnl/entry*100) if entry>0 else 0.0
        out=Lifecycle(timestamp,date,symbol,state,prev_state,side,instrument,label,round(current,2),round(entry,2),round(sl,2),round(t1,2),round(t2,2),round(t3,2),round(trail,2),round(pnl,2),round(pnlpct,2),action,reason,warnings)
        self._save(out); return out
