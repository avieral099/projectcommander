from pathlib import Path
import shutil
pipeline=Path('commander_pipeline.py'); dashboard=Path('dashboard.py')
if not pipeline.exists(): raise SystemExit('ERROR: commander_pipeline.py not found')
if not dashboard.exists(): raise SystemExit('ERROR: dashboard.py not found')
for src,bak in [(pipeline,Path('commander_pipeline_before_trade_lifecycle_v1.py')),(dashboard,Path('dashboard_before_trade_lifecycle_v1.py'))]:
    if not bak.exists(): shutil.copy2(src,bak)
s=pipeline.read_text(); imp='from trade_lifecycle_engine import TradeLifecycleEngine\n'; anchor='from straddle_structure_engine import StraddleStructureEngine\n'
if imp not in s:
    if anchor not in s: raise SystemExit('ERROR: pipeline import anchor not found')
    s=s.replace(anchor,anchor+imp,1)
block='''    try:\n        with TradeLifecycleEngine(db_path) as lifecycle_engine:\n            context.lifecycle = lifecycle_engine.evaluate(\n                context,\n                timestamp=timestamp,\n            )\n    except Exception as error:\n        context.set_error(\n            "trade_lifecycle_engine",\n            error,\n        )\n\n'''
if 'context.lifecycle =' not in s:
    a='    return context\n'; p=s.rfind(a)
    if p<0: raise SystemExit('ERROR: final return context not found')
    s=s[:p]+block+s[p:]
pipeline.write_text(s)
d=dashboard.read_text(); imp2='from trade_lifecycle_panel import print_trade_lifecycle\n'
if imp2 not in d:
    marker='from commander_summary_panel import (\n    print_commander_summary,\n)\n'
    if marker not in d: raise SystemExit('ERROR: dashboard summary import anchor not found')
    d=d.replace(marker,marker+imp2,1)
call='''\n        print_trade_lifecycle(\n            context\n        )\n'''
if 'print_trade_lifecycle(' not in d:
    marker='''        print_commander_summary(\n            context\n        )\n'''
    if marker not in d: raise SystemExit('ERROR: dashboard summary call anchor not found')
    d=d.replace(marker,marker+call,1)
dashboard.write_text(d)
print('TRADE LIFECYCLE V1 INSTALLED')
print('BACKUPS CREATED')
