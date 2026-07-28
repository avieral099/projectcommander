from pathlib import Path
import shutil
p=Path("dashboard.py"); b=Path("dashboard_before_cockpit_v1.py")
if not p.exists(): raise SystemExit("ERROR: dashboard.py not found")
s=p.read_text()
if not b.exists(): shutil.copy2(p,b)
block='''\n    return {\n        "generated_at": now.isoformat(),\n        "phase": str(phase),\n        "market_snapshots": market_snapshots,\n        "premium_snapshots": premium_snapshots,\n        "drivers": drivers,\n        "commander_contexts": commander_contexts,\n        "system_statuses": system_statuses,\n    }\n'''
anchor='\n\nif __name__ == "__main__":\n    main()\n'
if '"commander_contexts": commander_contexts' not in s:
    if anchor not in s: raise SystemExit("ERROR: dashboard final anchor not found")
    s=s.replace(anchor,block+anchor,1)
p.write_text(s)
print("COCKPIT V1 INSTALLED")
print(f"BACKUP: {b}")
