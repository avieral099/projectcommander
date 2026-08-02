from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

SERVICES = {
    "Commander CPU": {
        "pattern": "commander_cpu.py",
        "command": [
            "python3",
            "commander_cpu.py",
            "--allow-closed",
        ],
        "log": "logs/cpu.log",
    },
    "Chart Server": {
        "pattern": "chart_server.py",
        "command": [
            "python3",
            "chart_server.py",
        ],
        "log": "logs/chart.log",
    },
}

REQUIRED_FILES = [
    "commander_cpu.py",
    "chart_server.py",
    "commander_guard.py",
    "market_watch_terminal.py",
    "options_straddle_terminal.py",
    "execution_terminal.py",
    "dashboard_final_integrated.py",
]


def process_lines(pattern: str) -> list[str]:
    result = subprocess.run(
        ["ps", "-ef"],
        capture_output=True,
        text=True,
        check=True,
    )

    return [
        line
        for line in result.stdout.splitlines()
        if pattern in line
        and "grep" not in line
        and "commander_start.py" not in line
    ]


def verify_files() -> bool:
    missing = [
        file_name
        for file_name in REQUIRED_FILES
        if not Path(file_name).exists()
    ]

    if not missing:
        print("[PASS] Required files present")
        return True

    for file_name in missing:
        print(f"[FAIL] Missing file: {file_name}")

    return False


def start_service(
    name: str,
    pattern: str,
    command: list[str],
    log_path: str,
) -> bool:
    running = process_lines(pattern)

    if len(running) == 1:
        print(
            f"[PASS] {name:<20} "
            f"already running "
            f"PID={running[0].split()[1]}"
        )
        return True

    if len(running) > 1:
        print(
            f"[FAIL] {name:<20} "
            f"duplicate processes={len(running)}"
        )
        return False

    log = Path(log_path)
    log.parent.mkdir(parents=True, exist_ok=True)

    with log.open("a") as handle:
        process = subprocess.Popen(
            command,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    time.sleep(2)

    running_after = process_lines(pattern)

    if len(running_after) == 1:
        print(
            f"[START] {name:<20} "
            f"PID={process.pid}"
        )
        return True

    print(f"[FAIL] {name:<20} failed to start")
    return False


def print_manual_terminals() -> None:
    print()
    print("MANUAL TERMINALS")
    print("-" * 80)
    print(
        "Market Watch : "
        "python3 market_watch_terminal.py"
    )
    print(
        "Options      : "
        "python3 options_straddle_terminal.py"
    )
    print(
        "Execution    : "
        "python3 execution_terminal.py"
    )
    print(
        "Dashboard    : "
        "python3 dashboard_final_integrated.py"
    )
    print(
        "Chart URL    : "
        "http://127.0.0.1:8765"
    )


def run_guard() -> int:
    print()
    print("=" * 80)
    print("FINAL COMMANDER HEALTH")
    print("=" * 80)

    result = subprocess.run(
        ["python3", "commander_guard.py"],
        check=False,
    )

    return result.returncode


def main() -> None:
    print("=" * 80)
    print("COMMANDER START V1".center(80))
    print("=" * 80)

    if not verify_files():
        raise SystemExit(1)

    healthy = True

    for name, config in SERVICES.items():
        healthy &= start_service(
            name=name,
            pattern=config["pattern"],
            command=config["command"],
            log_path=config["log"],
        )

    print_manual_terminals()

    if not healthy:
        print()
        print("COMMANDER START : FAILED")
        raise SystemExit(1)

    print()
    print("BACKEND START   : PASS")

    guard_code = run_guard()

    if guard_code == 0:
        print("COMMANDER START : GREEN")
        return

    print(
        "COMMANDER START : BACKEND READY, "
        "MANUAL TERMINALS PENDING"
    )
    raise SystemExit(2)


if __name__ == "__main__":
    main()
