from pathlib import Path
import shutil

pairs = (
    (
        Path("decision_engine.py"),
        Path("decision_engine.py.v3"),
        Path("decision_engine_before_use_case_5_v3.py"),
    ),
    (
        Path("commander_summary_panel.py"),
        Path("commander_summary_panel.py.v3"),
        Path("commander_summary_panel_before_use_case_5_v3.py"),
    ),
)

for target, replacement, backup in pairs:
    if not target.exists():
        raise SystemExit(f"ERROR: {target} not found")
    if not replacement.exists():
        raise SystemExit(f"ERROR: {replacement} not found")
    if not backup.exists():
        shutil.copy2(target, backup)
    shutil.copy2(replacement, target)
    print(f"UPDATED: {target}")
    print(f"BACKUP : {backup}")

print("USE CASE 5 EXECUTION V3 INSTALLED")
