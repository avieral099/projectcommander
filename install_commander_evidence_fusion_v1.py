from pathlib import Path

required = (
    "commander_evidence_fusion.py",
    "commander_evidence_terminal.py",
)

missing = [name for name in required if not Path(name).exists()]
if missing:
    raise SystemExit("Missing files: " + ", ".join(missing))

print("COMMANDER EVIDENCE FUSION V1 FILES READY")
print("No production file was overwritten.")

if not Path("commander_decision_snapshot.json").exists():
    print("WARNING: commander_decision_snapshot.json missing.")
if not Path("market_health_snapshot.json").exists():
    print("WARNING: market_health_snapshot.json missing.")
