from pathlib import Path
import shutil

dashboard = Path("dashboard.py")
backup = Path("dashboard_before_summary_panel.py")

if not dashboard.exists():
    raise SystemExit("ERROR: dashboard.py not found")

source = dashboard.read_text()

if not backup.exists():
    shutil.copy2(dashboard, backup)

import_anchor = "from commander_terminal import (\n    print_commander_context,\n)\n"
import_block = "from commander_summary_panel import (\n    print_commander_summary,\n)\n"

if "from commander_summary_panel import" not in source:
    if import_anchor not in source:
        raise SystemExit("ERROR: import anchor not found")
    source = source.replace(import_anchor, import_anchor + import_block, 1)

call_anchor = "        print_commander_context(\n            context\n        )\n"
call_block = "\n        print_commander_summary(\n            context\n        )\n"

if "print_commander_summary(" not in source:
    if call_anchor not in source:
        raise SystemExit("ERROR: call anchor not found")
    source = source.replace(call_anchor, call_anchor + call_block, 1)

dashboard.write_text(source)
print("COMMANDER SUMMARY PANEL PATCHED")
print(f"BACKUP: {backup}")
