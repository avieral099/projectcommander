from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from commander_final_layer import apply_final_layer
from decision_engine import DecisionEngineV1
from reference_lock_engine import ReferenceLockEngine


def premium_snapshot():
    return {
        "index_name": "NIFTY",
        "expiry_date": "2026-07-28",
        "spot_price": 25110,
        "atm_strike": 25100,
        "atm_straddle": 240,
        "contracts": {
            "ATM_CE": {
                "strike": 25100,
                "option_type": "CE",
                "ltp": 125,
            },
            "ATM_PE": {
                "strike": 25100,
                "option_type": "PE",
                "ltp": 115,
            },
        },
    }


with TemporaryDirectory() as tmp:
    db = Path(tmp) / "commander.db"

    with ReferenceLockEngine(db) as engine:
        before = engine.process_session_locks(
            index_symbol="NSE:NIFTY50-INDEX",
            premium_snapshot=premium_snapshot(),
            now="2026-07-27T09:20:00+05:30",
        )

        assert (
            before["battle_0921"]["status"]
            == "AWAITING_LOCK_TIME"
        )

        after = engine.process_session_locks(
            index_symbol="NSE:NIFTY50-INDEX",
            premium_snapshot=premium_snapshot(),
            now="2026-07-27T09:25:00+05:30",
        )

        assert (
            after["battle_0921"]["status"]
            == "LOCKED"
        )
        assert (
            after["straddle_0925"]["status"]
            == "LOCKED"
        )

    call_flow = SimpleNamespace(
        dominant_side="CALL",
        call_leader_strike=25200,
        call_leader_label="OTM1_CE",
        put_leader_strike=25000,
        put_leader_label="OTM1_PE",
        migration_confidence=82,
    )

    structure = SimpleNamespace(
        straddle_bias="LONG_STRADDLE",
        short_straddle_stance="AVOID",
        structure_state="EXPANSION_BREAKOUT",
        confidence=90,
    )

    battle = SimpleNamespace(
        commander_status="ATTACK"
    )

    evidence = {
        "verdict": "CALL_BIAS",
        "call_confidence": 75,
        "put_confidence": 10,
    }

    decision = DecisionEngineV1().analyse(
        symbol="NSE:NIFTY50-INDEX",
        evidence=evidence,
        flow=call_flow,
        structure=structure,
        battle=battle,
        references={},
    )

    assert decision.action == "BUY_CALL"
    assert decision.instrument == "25200 CE"

    short_flow = SimpleNamespace(
        dominant_side="BALANCED",
        atm_strike=25100,
    )

    short_structure = SimpleNamespace(
        straddle_bias="SHORT_STRADDLE",
        short_straddle_stance="FAVOURABLE",
        structure_state="DECAY_BREAKDOWN",
        confidence=88,
    )

    short_decision = DecisionEngineV1().analyse(
        symbol="NSE:NIFTY50-INDEX",
        evidence={
            "verdict": "NO_BIAS",
            "call_confidence": 15,
            "put_confidence": 12,
        },
        flow=short_flow,
        structure=short_structure,
        battle=SimpleNamespace(
            commander_status="WAIT"
        ),
        references=after,
    )

    assert (
        short_decision.action
        == "SHORT_STRADDLE"
    )

    context = SimpleNamespace(
        symbol="NSE:NIFTY50-INDEX",
        snapshot=premium_snapshot(),
        behaviour=None,
        flow=call_flow,
        structure=structure,
        battle=battle,
        evidence=evidence,
    )

    result = apply_final_layer(
        context,
        db_path=db,
        timestamp="2026-07-27T09:26:00+05:30",
    )

    assert result["decision"].action == "BUY_CALL"
    assert hasattr(context, "references")
    assert hasattr(context, "decision")


print(
    "ALL OPERATION COMMANDER COMPLETION V1 "
    "TESTS PASSED"
)
