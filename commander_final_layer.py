"""
OPERATION COMMANDER
Module  : Final Layer V1
Purpose : Existing CommanderContext par reference locks aur decision attach karna.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from decision_engine import (
    DecisionEngineV1,
    print_decision,
)
from reference_lock_engine import (
    DEFAULT_DB_PATH,
    ReferenceLockEngine,
)


def apply_final_layer(
    context: Any,
    *,
    market_snapshot: Optional[Dict[str, Any]] = None,
    db_path: str | Path = DEFAULT_DB_PATH,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    if context.snapshot is None:
        raise RuntimeError(
            "Premium snapshot unavailable; final layer cannot run"
        )

    with ReferenceLockEngine(db_path) as engine:
        references = engine.process_session_locks(
            index_symbol=context.symbol,
            premium_snapshot=context.snapshot,
            market_snapshot=market_snapshot,
            behaviour=context.behaviour,
            flow=context.flow,
            structure=context.structure,
            battle=context.battle,
            now=timestamp,
        )

    decision = DecisionEngineV1().analyse(
        symbol=context.symbol,
        evidence=context.evidence,
        flow=context.flow,
        structure=context.structure,
        battle=context.battle,
        references=references,
    )

    context.references = references
    context.decision = decision

    return {
        "references": references,
        "decision": decision,
    }


def print_final_layer(
    context: Any,
    width: int = 100,
) -> None:
    references = getattr(
        context,
        "references",
        {},
    )

    print("\n" + "=" * width)
    print("COMMANDER REFERENCE LOCKS".center(width))
    print("=" * width)

    for label, result in references.items():
        reference = result.get("reference") or {}

        print(
            f"{label.upper():<28}: "
            f"{result.get('status')} | "
            f"STRADDLE "
            f"₹{float(reference.get('atm_straddle') or 0.0):.2f}"
        )

    decision = getattr(
        context,
        "decision",
        None,
    )

    if decision:
        print_decision(
            decision,
            width=width,
        )
