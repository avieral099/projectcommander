OPERATION COMMANDER — DRIVER EVIDENCE ADAPTER V1
================================================

PURPOSE
-------
Reads an existing Driver Engine JSON output and creates:

driver_evidence_snapshot.json

The existing Evidence Fusion V1 will automatically consume this file.

AUTO-DISCOVERY CANDIDATES
-------------------------
driver_snapshot.json
driver_engine_snapshot.json
driver_evidence.json
commander_driver_snapshot.json
live_cache.json
market_structure_snapshot.json

COPY
----
Copy every file into projectcommander.

INSTALL
-------
python3 install_driver_evidence_adapter_v1.py

COMPILE
-------
python3 -m py_compile driver_evidence_adapter.py driver_evidence_terminal.py

TEST
----
python3 test_driver_evidence_adapter_v1.py

AUTO-DISCOVER AND RUN
---------------------
python3 driver_evidence_terminal.py --once

EXPLICIT SOURCE
---------------
python3 driver_evidence_terminal.py --once --json-source YOUR_DRIVER_FILE.json

THEN RUN FUSION
---------------
python3 commander_evidence_terminal.py --once

EXPECTED RESULT
---------------
MARKET    CONNECTED
PREMIUM   CONNECTED
DRIVERS   CONNECTED or PARTIAL

IMPORTANT
---------
The adapter does not invent missing drivers.
If no usable rows exist, STATUS remains PARTIAL and execution stays locked.
