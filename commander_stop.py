from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

SERVICES = {
    "Commander CPU": "commander_cpu.py",
    "Dashboard": "dashboard_final_integrated.py",
    "Market Watch": "market_watch_terminal.py",
    "Options Terminal": "options_straddle_terminal.py",
    "Execution Terminal": "execution_terminal.py",
    "Chart Server": "chart_server.py",
}

LOCK_FILES = [
    ".commander_cpu.lock",
    ".dashboard.lock",
    ".chart_server.lock",
    ".market_watch.lock",
    ".options_terminal.lock",
    ".execution_terminal.lock",
]


def processes(pattern: str) -> list[tuple[int, str]]:
    result = subprocess.run(
        ["ps", "-ef"],
        capture_output=True,
        text=True,
        check=True,
    )

    found = []

    for line in result.stdout.splitlines():
        if (
            pattern in line
            and "grep" not in line
            and "commander_stop.py" not in line
        ):
            parts = line.split()

            if len(parts) >= 2:
                found.append(
                    (
                        int(parts[1]),
                        line,
                    )
                )

    return found


def stop_service(
    name: str,
    pattern: str,
) -> bool:
    running = processes(pattern)

    if not running:
        print(f"[PASS] {name:<20} already stopped")
        return True

    for pid, _ in running:
        try:
            os.kill(pid, signal.SIGTERM)
            print(
                f"[STOP] {name:<20} "
                f"PID={pid}"
            )
        except ProcessLookupError:
            pass

    deadline = time.time() + 5

    while time.time() < deadline:
        if not processes(pattern):
            return True

        time.sleep(0.25)

    remaining = processes(pattern)

    for pid, _ in remaining:
        try:
            os.kill(pid, signal.SIGKILL)
            print(
                f"[KILL] {name:<20} "
                f"PID={pid}"
            )
        except ProcessLookupError:
            pass

    time.sleep(1)
    return not processes(pattern)


def clear_runtime_locks() -> None:
    for file_name in LOCK_FILES:
        path = Path(file_name)

        if path.exists():
            try:
                path.unlink()
                print(f"[CLEAN] Runtime lock removed: {file_name}")
            except OSError as error:
                print(
                    f"[WARN] Could not remove "
                    f"{file_name}: {error}"
                )


def verify_shutdown() -> bool:
    print()
    print("=" * 80)
    print("FINAL SHUTDOWN VERIFICATION".center(80))
    print("=" * 80)

    clean = True

    for name, pattern in SERVICES.items():
        count = len(processes(pattern))

        if count == 0:
            print(f"[PASS] {name:<20} stopped")
        else:
            clean = False
            print(
                f"[FAIL] {name:<20} "
                f"remaining={count}"
            )

    return clean


def main() -> None:
    print("=" * 80)
    print("COMMANDER STOP V1".center(80))
    print("=" * 80)

    clean = True

    for name, pattern in SERVICES.items():
        clean &= stop_service(name, pattern)

    clear_runtime_locks()

    verified = verify_shutdown()

    print("=" * 80)

    if clean and verified:
        print("COMMANDER SHUTDOWN : CLEAN")
        return

    print("COMMANDER SHUTDOWN : INCOMPLETE")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
