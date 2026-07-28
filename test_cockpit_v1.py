from pathlib import Path
from tempfile import TemporaryDirectory
from commander_state_store import write_state,read_state
with TemporaryDirectory() as d:
    p=Path(d)/"x.json";write_state(p,{"phase":"TEST"});assert read_state(p)["phase"]=="TEST"
print("ALL COMMANDER COCKPIT V1 TESTS PASSED")
