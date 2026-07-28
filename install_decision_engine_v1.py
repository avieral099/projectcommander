from pathlib import Path
import shutil

pipeline = Path("commander_pipeline.py")
backup = Path("commander_pipeline_before_decision_engine.py")

if not pipeline.exists():
    raise SystemExit("ERROR: commander_pipeline.py not found")

source = pipeline.read_text()

if not backup.exists():
    shutil.copy2(pipeline, backup)

import_line = "from decision_engine import generate_decision\n"
anchor = "from commander_context import CommanderContext\n"

if import_line not in source:
    if anchor not in source:
        raise SystemExit("ERROR: import anchor not found")
    source = source.replace(anchor, anchor + import_line, 1)

decision_block = '''    try:
        context.decision = generate_decision(
            context
        )
    except Exception as error:
        context.set_error(
            "decision_engine",
            error,
        )

'''

if "context.decision = generate_decision(" not in source:
    anchor = "    return context\n"
    if anchor not in source:
        raise SystemExit("ERROR: return context anchor not found")
    source = source.replace(anchor, decision_block + anchor, 1)

pipeline.write_text(source)
print("DECISION ENGINE V1 PATCHED")
print(f"BACKUP: {backup}")
