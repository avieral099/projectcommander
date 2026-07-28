from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from trade_lifecycle_engine import TradeLifecycleEngine

def ctx(price,ts='2026-07-28T09:30:00+05:30'):
    return SimpleNamespace(symbol='NSE:NIFTY50-INDEX',recorder_result={'timestamp':ts},decision=SimpleNamespace(action='BUY_CALL',side='CALL',instrument='23950 CE',strike_label='ATM_CE',entry_reference=100,entry_trigger=100,stop_loss=85,target_1=120,target_2=135,target_3=150),snapshot={'contracts':{'ATM_CE':{'strike':23950,'option_type':'CE','ltp':price,'ask':price}}})
with TemporaryDirectory() as td:
    with TradeLifecycleEngine(Path(td)/'x.db') as e:
        a=e.evaluate(ctx(101)); assert a.state=='ACTIVE'
        b=e.evaluate(ctx(122,'2026-07-28T09:31:00+05:30')); assert b.state=='TARGET_1_HIT' and b.trail_stop==100
        c=e.evaluate(ctx(99,'2026-07-28T09:32:00+05:30')); assert c.state=='STOP_HIT' and c.action=='EXIT'
        n=e.connection.execute('SELECT COUNT(*) c FROM trade_lifecycle_events').fetchone()['c']; assert n==3
print('ALL TRADE LIFECYCLE V1 TESTS PASSED')
