from commander_pipeline import run_pipeline
from commander_terminal import (
    print_commander_context,
)


SYMBOLS = [
    "NSE:NIFTY50-INDEX",
    "NSE:NIFTYBANK-INDEX",
    "BSE:SENSEX-INDEX",
]


def main() -> None:
    for symbol in SYMBOLS:
        context = run_pipeline(
            symbol,
            market_snapshot=None,
            drivers=None,
            battle_reference=None,
        )

        print_commander_context(
            context
        )


if __name__ == "__main__":
    main()
