#!/usr/bin/env python3
"""
Operation Commander — Unified Audit
Run:
    python3 commander_audit.py

Purpose:
- Detect the SQLite database and available tables.
- Report recorded session duration from strike_straddle_minute_bars.
- Report row count and last observations.
- Show recent reference locks, strike rotations, intelligence summaries,
  trade lifecycle events, and session anchors when present.
- Show recent macOS reboot and power events.
- Never assume optional table schemas; it introspects before querying.
"""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_DB = "premium_intelligence_1m.db"


def run_shell(command: str) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        output = (result.stdout or result.stderr).strip()
        return output or "No output"
    except Exception as exc:
        return f"Unavailable: {exc}"


def connect_database(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return {str(row["name"]) for row in rows}


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    safe_table = table.replace('"', '""')
    rows = connection.execute(f'PRAGMA table_info("{safe_table}")').fetchall()
    return [str(row["name"]) for row in rows]


def first_existing(columns: Sequence[str], candidates: Iterable[str]) -> str | None:
    available = set(columns)
    return next((item for item in candidates if item in available), None)


def print_rows(title: str, rows: Sequence[sqlite3.Row], limit: int = 10) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    if not rows:
        print("No rows found.")
        return
    for row in rows[:limit]:
        print(" | ".join(f"{key}={row[key]}" for key in row.keys()))


def audit_straddle(
    connection: sqlite3.Connection,
    tables: set[str],
    trading_date: str,
) -> None:
    table = "strike_straddle_minute_bars"
    print("\nSESSION RECORDING")
    print("-----------------")
    if table not in tables:
        print(f"Missing table: {table}")
        return

    columns = table_columns(connection, table)
    timestamp_col = first_existing(columns, ["timestamp", "datetime", "time"])
    date_col = first_existing(columns, ["trading_date", "date", "session_date"])

    if not timestamp_col:
        print("No timestamp column detected.")
        return

    where = ""
    params: tuple[object, ...] = ()
    if date_col:
        where = f' WHERE "{date_col}" = ?'
        params = (trading_date,)

    query = (
        f'SELECT MIN("{timestamp_col}") AS first_record, '
        f'MAX("{timestamp_col}") AS last_record, '
        f'ROUND((julianday(MAX("{timestamp_col}")) - '
        f'julianday(MIN("{timestamp_col}"))) * 24 * 60, 1) AS duration_minutes, '
        f'COUNT(*) AS rows_recorded '
        f'FROM "{table}"{where}'
    )
    summary = connection.execute(query, params).fetchone()

    print(f"Trading date      : {trading_date}")
    print(f"First record      : {summary['first_record']}")
    print(f"Last record       : {summary['last_record']}")
    print(f"Recorded duration : {summary['duration_minutes']} minutes")
    print(f"Rows recorded     : {summary['rows_recorded']}")

    desired = [
        name
        for name in ["timestamp", "index_name", "spot_price", "atm_strike",
                     "strike", "ce_ltp", "pe_ltp", "straddle", "change_1m"]
        if name in columns
    ]
    if desired:
        select_list = ", ".join(f'"{name}"' for name in desired)
        recent = connection.execute(
            f'SELECT {select_list} FROM "{table}" '
            f'ORDER BY "{timestamp_col}" DESC LIMIT 5'
        ).fetchall()
        print_rows("LAST 5 STRADDLE OBSERVATIONS", recent, 5)


def audit_optional_table(
    connection: sqlite3.Connection,
    tables: set[str],
    table: str,
    title: str,
    limit: int = 20,
) -> None:
    if table not in tables:
        print(f"\n{title}\n{'-' * len(title)}\nTable not present.")
        return

    columns = table_columns(connection, table)
    order_col = first_existing(
        columns,
        ["timestamp", "created_at", "event_time", "id", "trading_date", "date"],
    )
    order_clause = f' ORDER BY "{order_col}" DESC' if order_col else ""
    rows = connection.execute(
        f'SELECT * FROM "{table}"{order_clause} LIMIT ?', (limit,)
    ).fetchall()
    print_rows(title, rows, limit)


def main() -> int:
    parser = argparse.ArgumentParser(description="Operation Commander audit")
    parser.add_argument("--db", default=DEFAULT_DB, help="SQLite database path")
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Trading date in YYYY-MM-DD format",
    )
    args = parser.parse_args()

    print("=" * 72)
    print("                 OPERATION COMMANDER — AUDIT")
    print("=" * 72)

    db_path = Path(args.db).expanduser().resolve()
    print(f"Database          : {db_path}")
    print(f"Audit date        : {args.date}")

    try:
        connection = connect_database(db_path)
    except Exception as exc:
        print(f"\nAUDIT FAILED: {exc}")
        return 1

    try:
        tables = table_names(connection)
        print(f"Detected tables   : {', '.join(sorted(tables)) or 'None'}")

        audit_straddle(connection, tables, args.date)

        audit_optional_table(
            connection, tables, "reference_locks", "REFERENCE LOCKS", 20
        )
        audit_optional_table(
            connection, tables, "strike_rotations", "STRIKE ROTATIONS", 20
        )
        audit_optional_table(
            connection, tables, "session_anchors", "SESSION ANCHORS", 20
        )
        audit_optional_table(
            connection,
            tables,
            "intelligence_summaries",
            "INTELLIGENCE SUMMARIES",
            20,
        )
        audit_optional_table(
            connection,
            tables,
            "trade_lifecycle_events",
            "TRADE LIFECYCLE EVENTS",
            20,
        )

        print("\nMAC POWER AUDIT")
        print("---------------")
        print("Recent reboot/shutdown:")
        print(run_shell("last reboot | head"))
        print("\nRecent sleep/wake/start/shutdown events:")
        print(
            run_shell(
                'pmset -g log | egrep "Wake|Sleep|Shutdown|Start" | tail -30'
            )
        )

        print("\nAUDIT NOTES")
        print("-----------")
        print("- SQLite is treated as the primary source of truth.")
        print("- Recorded duration is the first-to-last persisted data window.")
        print("- Exact process uptime requires session start/heartbeat/stop logging.")
        print("- Terminal-only observations cannot be recovered after a shutdown.")
        print("=" * 72)
        return 0
    except sqlite3.Error as exc:
        print(f"\nDATABASE AUDIT FAILED: {exc}")
        return 2
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())
