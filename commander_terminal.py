from __future__ import annotations

from typing import Any

from commander_context import CommanderContext


def _value(
    obj: Any,
    name: str,
    default: Any = "NOT AVAILABLE",
) -> Any:
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(name, default)

    return getattr(obj, name, default)


def print_commander_context(
    context: CommanderContext,
    width: int = 100,
) -> None:
    print("\n" + "=" * width)
    print(
        "OPERATION COMMANDER — PIPELINE V2".center(
            width
        )
    )
    print("=" * width)

    print(
        f"SYMBOL                    : "
        f"{context.symbol}"
    )

    print("-" * width)

    print(
        f"RECORDER                  : "
        f"{_value(context.recorder_result, 'status')}"
    )
    print(
        f"CONTRACTS RECORDED        : "
        f"{_value(context.recorder_result, 'contracts_inserted', 0)}"
    )
    print(
        f"STRADDLES RECORDED        : "
        f"{_value(context.recorder_result, 'straddles_inserted', 0)}"
    )

    print("-" * width)

    print(
        f"PREMIUM REGIME            : "
        f"{_value(context.behaviour, 'regime')}"
    )
    print(
        f"PREMIUM VIEW              : "
        f"{_value(context.behaviour, 'commander_view')}"
    )

    print("-" * width)

    print(
        f"DOMINANT PREMIUM SIDE     : "
        f"{_value(context.flow, 'dominant_side')}"
    )
    print(
        f"CALL LEADER               : "
        f"{_value(context.flow, 'call_leader_display')}"
    )
    print(
        f"PUT LEADER                : "
        f"{_value(context.flow, 'put_leader_display')}"
    )
    print(
        f"ATM EROSION DESTINATION   : "
        f"{_value(context.flow, 'atm_erosion_destination')}"
    )

    print("-" * width)

    print(
        f"STRADDLE STRUCTURE        : "
        f"{_value(context.structure, 'structure_state')}"
    )
    print(
        f"STRADDLE BIAS             : "
        f"{_value(context.structure, 'straddle_bias')}"
    )
    print(
        f"SHORT STRADDLE STANCE     : "
        f"{_value(context.structure, 'short_straddle_stance')}"
    )

    print("-" * width)

    print(
        f"BATTLE ZONE               : "
        f"{_value(context.battle, 'zone')}"
    )
    print(
        f"BATTLE STATUS             : "
        f"{_value(context.battle, 'commander_status')}"
    )
    print(
        f"BATTLE SCORE              : "
        f"{_value(context.battle, 'battle_score')}"
    )

    print("-" * width)

    print(
        f"EVIDENCE VERDICT          : "
        f"{_value(context.evidence, 'verdict')}"
    )
    print(
        f"EVIDENCE SCORE            : "
        f"{float(_value(context.evidence, 'score', 0.0)):.2f}%"
    )
    print(
        f"CALL CONFIDENCE           : "
        f"{float(_value(context.evidence, 'call_confidence', 0.0)):.2f}%"
    )
    print(
        f"PUT CONFIDENCE            : "
        f"{float(_value(context.evidence, 'put_confidence', 0.0)):.2f}%"
    )
    print(
        f"ENGINE AGREEMENT          : "
        f"{_value(context.evidence, 'agreement', 0)}"
    )

    if context.errors:
        print("-" * width)
        print("ENGINE ERRORS")

        for engine, message in (
            context.errors.items()
        ):
            print(
                f"{engine:<28}: {message}"
            )

    print("=" * width)
