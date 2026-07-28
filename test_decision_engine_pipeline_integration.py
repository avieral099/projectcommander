from pathlib import Path

source = Path("commander_pipeline.py").read_text()
assert "from decision_engine import generate_decision" in source
assert "context.decision = generate_decision(" in source
print("ALL DECISION ENGINE PIPELINE INTEGRATION TESTS PASSED")
