from __future__ import annotations
from typing import Any

def _g(o,n,d=None):
    if o is None:return d
    return o.get(n,d) if isinstance(o,dict) else getattr(o,n,d)
def _f(v,d=0.0):
    try:return float(v)
    except (TypeError,ValueError):return d

def print_trade_lifecycle(context:Any,width:int=92)->None:
    x=_g(context,'lifecycle',None)
    if x is None:return
    print('\n'+'='*width); print('COMMANDER — TRADE LIFECYCLE'.center(width)); print('='*width)
    print(f"STATE                     : {_g(x,'state','UNKNOWN')}")
    print(f"ACTION                    : {_g(x,'action','WAIT')}")
    print(f"INSTRUMENT                : {_g(x,'instrument','NOT_SELECTED')}")
    print(f"CURRENT PREMIUM           : ₹{_f(_g(x,'current_price',0)):.2f}")
    print(f"VIRTUAL ENTRY             : ₹{_f(_g(x,'entry_price',0)):.2f}")
    print(f"STOP LOSS                 : ₹{_f(_g(x,'stop_loss',0)):.2f}")
    print(f"TRAIL STOP                : ₹{_f(_g(x,'trail_stop',0)):.2f}")
    print(f"TARGET 1 / 2 / 3          : ₹{_f(_g(x,'target_1',0)):.2f} / ₹{_f(_g(x,'target_2',0)):.2f} / ₹{_f(_g(x,'target_3',0)):.2f}")
    print(f"VIRTUAL P&L               : {_f(_g(x,'pnl_points',0)):+.2f} ({_f(_g(x,'pnl_percent',0)):+.2f}%)")
    print(f"REASON                    : {_g(x,'reason','UNKNOWN')}")
    for w in list(_g(x,'warnings',[]) or []): print(f'! {w}')
    print('='*width)
