"""
OPERATION COMMANDER
Module  : Live Runner V1
Purpose : dashboard.py ko market session mein har 60 seconds refresh karna.

Features
--------
- One dashboard snapshot per minute
- Old terminal screen clear
- Errors do not kill the runner
- Pre-market waiting
- Automatic stop after 15:30 IST
- KeyboardInterrupt safe shutdown
"""

from __future__ import annotations

import os
import time
import traceback
from datetime import datetime, time as clock_time
from zoneinfo import ZoneInfo

import dashboard


IST = ZoneInfo("Asia/Kolkata")

REFRESH_SECONDS = 60
RETRY_SECONDS = 20

PRE_MARKET_START = clock_time(8, 30)
MARKET_OPEN = clock_time(9, 15)
MARKET_CLOSE = clock_time(15, 30)


def clear_terminal() -> None:
    os.system(
        "clear"
        if os.name != "nt"
        else "cls"
    )


def now_ist() -> datetime:
    return datetime.now(IST)


def seconds_until_next_minute(
    current: datetime,
) -> int:
    seconds = 60 - current.second

    if seconds <= 0:
        return REFRESH_SECONDS

    return seconds


def print_waiting_message(
    current: datetime,
) -> None:
    clear_terminal()

    print("=" * 92)
    print(
        "OPERATION COMMANDER — LIVE RUNNER".center(
            92
        )
    )
    print("=" * 92)
    print(
        f"TIME                      : "
        f"{current.strftime('%H:%M:%S')} IST"
    )
    print(
        "STATUS                    : "
        "AWAITING MARKET SESSION"
    )
    print(
        "MARKET OPEN               : "
        "09:15 IST"
    )
    print(
        "AUTO REFRESH              : "
        "EVERY 60 SECONDS"
    )
    print("=" * 92)


def run_dashboard_snapshot() -> bool:
    try:
        clear_terminal()
        dashboard.main()
        return True

    except Exception:
        print("\n" + "=" * 92)
        print(
            "COMMANDER SNAPSHOT ERROR".center(
                92
            )
        )
        print("=" * 92)
        traceback.print_exc()
        print("=" * 92)
        print(
            f"RETRYING IN               : "
            f"{RETRY_SECONDS} SECONDS"
        )
        return False


def main() -> None:
    print(
        "OPERATION COMMANDER LIVE RUNNER STARTED"
    )

    while True:
        current = now_ist()
        current_time = current.time().replace(
            tzinfo=None
        )

        if current_time >= MARKET_CLOSE:
            clear_terminal()

            print("=" * 92)
            print(
                "OPERATION COMMANDER — MISSION COMPLETE".center(
                    92
                )
            )
            print("=" * 92)
            print(
                f"MARKET CLOSE              : "
                f"{current.strftime('%Y-%m-%d %H:%M:%S')} IST"
            )
            print(
                "STATUS                    : "
                "LIVE RUNNER STOPPED"
            )
            print("=" * 92)
            break

        if current_time < MARKET_OPEN:
            print_waiting_message(
                current
            )

            wait_seconds = min(
                seconds_until_next_minute(
                    current
                ),
                REFRESH_SECONDS,
            )

            time.sleep(
                max(wait_seconds, 1)
            )
            continue

        success = run_dashboard_snapshot()

        if success:
            current = now_ist()
            wait_seconds = (
                seconds_until_next_minute(
                    current
                )
            )
        else:
            wait_seconds = RETRY_SECONDS

        time.sleep(
            max(wait_seconds, 1)
        )


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print(
            "\nCOMMANDER LIVE RUNNER "
            "STOPPED MANUALLY"
        )
