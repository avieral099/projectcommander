from __future__ import annotations

import subprocess
import sys

SERVICES = {
    "Commander CPU": "commander_cpu.py",
    "Dashboard": "dashboard_final_integrated.py",
    "Market Watch": "market_watch_terminal.py",
    "Options Terminal": "options_straddle_terminal.py",
    "Execution Terminal": "execution_terminal.py",
    "Chart Server": "chart_server.py",
}


def pids(pattern: str) -> list[str]:
    output = subprocess.run(
        [
            "ps",
            "-ef",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    result = []

    for line in output.splitlines():
        if pattern in line and "grep" not in line:
            result.append(line)

    return result


def status(name: str, pattern: str) -> bool:
    running = pids(pattern)

    if len(running) == 1:
        print(f"[PASS] {name:<20} PID={running[0].split()[1]}")
        return True

    if len(running) == 0:
        print(f"[FAIL] {name:<20} NOT RUNNING")
        return False

    print(f"[FAIL] {name:<20} DUPLICATE ({len(running)})")

    for process in running:
        print(f"       {process}")

    return False


def main() -> None:
    print("=" * 80)
    print("COMMANDER GUARD V1".center(80))
    print("=" * 80)

    ok = True

    for name, pattern in SERVICES.items():
        ok &= status(name, pattern)

    print("=" * 80)

    if ok:
        print("COMMANDER HEALTH : GREEN")
        sys.exit(0)

    print("COMMANDER HEALTH : RED")
    sys.exit(1)


if __name__ == "__main__":
    main()
