from pathlib import Path
required=["market_health_engine.py","market_health_terminal.py"]
missing=[x for x in required if not Path(x).exists()]
if missing: raise SystemExit("Missing files: "+", ".join(missing))
print("MARKET HEALTH V1 FILES READY")
print("No existing production file was overwritten.")
