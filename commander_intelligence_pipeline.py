from __future__ import annotations

import argparse
import subprocess
import sys


def run(command: list[str]) -> None:
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run structure, health and decision snapshots in order."
    )
    parser.add_argument("--skip-scan", action="store_true")
    args = parser.parse_args()

    if not args.skip_scan:
        run([sys.executable, "market_structure_scanner.py"])

    run([sys.executable, "market_health_terminal.py", "--once"])
    run([sys.executable, "commander_decision_terminal.py", "--once"])


if __name__ == "__main__":
    main()
