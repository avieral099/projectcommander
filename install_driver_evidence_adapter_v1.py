from pathlib import Path

required = (
    "driver_evidence_adapter.py",
    "driver_evidence_terminal.py",
)

missing = [name for name in required if not Path(name).exists()]
if missing:
    raise SystemExit("Missing files: " + ", ".join(missing))

print("DRIVER EVIDENCE ADAPTER V1 FILES READY")
print("No production file was overwritten.")

candidates = (
    "driver_snapshot.json",
    "driver_engine_snapshot.json",
    "driver_evidence.json",
    "commander_driver_snapshot.json",
    "live_cache.json",
    "market_structure_snapshot.json",
)

found = [name for name in candidates if Path(name).exists()]
if found:
    print("SOURCE CANDIDATES FOUND: " + ", ".join(found))
else:
    print("WARNING: No standard driver JSON candidate found.")
