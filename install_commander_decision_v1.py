from __future__ import annotations

from pathlib import Path


required = (
    "commander_decision_engine.py",
    "commander_decision_terminal.py",
    "commander_intelligence_pipeline.py",
)

missing = [name for name in required if not Path(name).exists()]
if missing:
    raise SystemExit("Missing files: " + ", ".join(missing))

print("COMMANDER DECISION V1 FILES READY")
print("No production file was overwritten.")

if not Path("market_health_snapshot.json").exists():
    print("WARNING: market_health_snapshot.json is not present.")
    print("Run: python3 market_health_terminal.py --once")
