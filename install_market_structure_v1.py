from __future__ import annotations

from pathlib import Path
import shutil


FILES = (
    "market_structure_5m_engine.py",
    "daily_structure_engine.py",
    "market_scanner_provider.py",
    "market_scanner_config.json",
    "market_structure_scanner.py",
    "market_watch_terminal_v2.py",
)

missing = [name for name in FILES if not Path(name).exists()]
if missing:
    raise SystemExit("Missing files: " + ", ".join(missing))

current = Path("market_watch_terminal.py")
backup = Path("market_watch_terminal_before_structure_v1.py")

if current.exists() and not backup.exists():
    shutil.copy2(current, backup)

print("MARKET STRUCTURE V1 FILES READY")
if current.exists():
    print("Existing market_watch_terminal.py preserved.")
    print("New terminal entry point: market_watch_terminal_v2.py")
print("No production file was overwritten.")
