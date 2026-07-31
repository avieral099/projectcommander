import argparse
import os
import sqlite3
import time

from cockpit_config import (
    OPTION_INDEXES,
    TERMINAL_REFRESH_SECONDS,
)

DB = "premium_intelligence_1m.db"
WIDTH = 100


def fetch_index_data(symbol):
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row

    try:
        summary = connection.execute(
            """
            SELECT *
            FROM intelligence_summaries
            WHERE index_symbol=?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (symbol,),
        ).fetchone()

        if not summary:
            return None, [], []

        rows = connection.execute(
            """
            SELECT
                ladder_label,
                strike,
                option_type,
                ltp,
                bid,
                ask,
                oi,
                volume,
                iv
            FROM option_minute_bars
            WHERE timestamp=?
              AND index_symbol=?
            ORDER BY strike, option_type
            """,
            (
                summary["timestamp"],
                symbol,
            ),
        ).fetchall()

        locks = connection.execute(
            """
            SELECT
                reference_type,
                straddle
            FROM reference_locks
            WHERE index_symbol=?
            ORDER BY lock_time DESC
            LIMIT 2
            """,
            (symbol,),
        ).fetchall()

        return summary, rows, locks

    finally:
        connection.close()


def print_index(name, symbol):
    print("=" * WIDTH)
    print(
        f"COMMANDER — OPTIONS / STRADDLE — {name}".center(WIDTH)
    )
    print("=" * WIDTH)

    try:
        summary, rows, locks = fetch_index_data(symbol)

        if not summary:
            print("NO OPTION DATA YET")
            return

        print(
            f"TIME {summary['timestamp']} | "
            f"SPOT {summary['spot_price']:.2f} | "
            f"ATM {summary['atm_strike']} | "
            f"STRADDLE ₹{summary['atm_straddle']:.2f}"
        )

        print(
            f"DECAY {summary['decay_state']} | "
            f"ROTATION {summary['rotation_state']} | "
            f"COMMANDER {summary['commander_state']}"
        )

        if locks:
            print(
                "LOCKS: "
                + " | ".join(
                    f"{row['reference_type']} "
                    f"₹{row['straddle']:.2f}"
                    for row in locks
                )
            )
        else:
            print("LOCKS: AWAITING")

        print("-" * WIDTH)
        print(
            f"{'LABEL':<11}"
            f"{'STRIKE':>8}"
            f"{'TYPE':>6}"
            f"{'LTP':>10}"
            f"{'BID':>10}"
            f"{'ASK':>10}"
            f"{'OI':>13}"
            f"{'VOL':>13}"
            f"{'IV':>8}"
        )
        print("-" * WIDTH)

        for row in rows:
            print(
                f"{row['ladder_label']:<11}"
                f"{row['strike']:>8}"
                f"{row['option_type']:>6}"
                f"{row['ltp']:>10.2f}"
                f"{row['bid']:>10.2f}"
                f"{row['ask']:>10.2f}"
                f"{row['oi']:>13}"
                f"{row['volume']:>13}"
                f"{row['iv']:>8.2f}"
            )

    except Exception as error:
        print(f"DB ERROR: {error}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--index",
        choices=["all", "1", "2", "3"],
        default="all",
    )
    args = parser.parse_args()

    while True:
        os.system("clear")

        if args.index == "all":
            selected = OPTION_INDEXES.items()
        else:
            selected = [
                (
                    args.index,
                    OPTION_INDEXES[args.index],
                )
            ]

        for _, index_data in selected:
            name, symbol = index_data
            print_index(name, symbol)
            print()

        time.sleep(TERMINAL_REFRESH_SECONDS)


if __name__ == "__main__":
    main()
