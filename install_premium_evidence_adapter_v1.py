from pathlib import Path

required = (
    "premium_evidence_adapter.py",
    "premium_evidence_terminal.py",
)

missing = [name for name in required if not Path(name).exists()]
if missing:
    raise SystemExit("Missing files: " + ", ".join(missing))

print("PREMIUM EVIDENCE ADAPTER V1 FILES READY")
print("No production file was overwritten.")

sources = [
    "premium_intelligence_1m.db",
    "premium_intelligence.db",
    "premium_snapshot.json",
    "premium_intelligence_snapshot.json",
]

found = [name for name in sources if Path(name).exists()]
if found:
    print("SOURCE CANDIDATES FOUND: " + ", ".join(found))
else:
    print("WARNING: No standard premium source candidate found.")
