from __future__ import annotations
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
IST = ZoneInfo("Asia/Kolkata")
def serialise(value: Any) -> Any:
    if value is None or isinstance(value,(str,int,float,bool)): return value
    if is_dataclass(value): return serialise(asdict(value))
    if isinstance(value,dict): return {str(k):serialise(v) for k,v in value.items()}
    if isinstance(value,(list,tuple,set)): return [serialise(v) for v in value]
    if hasattr(value,"__dict__"): return serialise(vars(value))
    return str(value)
def context_to_dict(context: Any) -> dict[str,Any]:
    fields=("symbol","snapshot","recorder_result","behaviour","flow","structure","battle","evidence","observations","events","decision","lifecycle","validation","errors")
    return {name:serialise(getattr(context,name,None)) for name in fields} if context else {}
def write_state(path,payload):
    target=Path(path); temp=target.with_suffix(target.suffix+".tmp"); payload=dict(payload); payload["state_written_at"]=datetime.now(IST).isoformat(); temp.write_text(json.dumps(serialise(payload),indent=2)); temp.replace(target)
def read_state(path):
    target=Path(path)
    if not target.exists(): return {}
    try:return json.loads(target.read_text())
    except (OSError,json.JSONDecodeError):return {}
