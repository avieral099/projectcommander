import sys
import types


battle_engine = types.ModuleType(
    "battle_engine"
)


class Battle:
    zone = "EXPANSION_ZONE"
    battle_score = 7
    commander_status = "ATTACK"


battle_engine.evaluate = (
    lambda **kwargs: Battle()
)
sys.modules["battle_engine"] = battle_engine


evidence_engine = types.ModuleType(
    "evidence_engine"
)


def build_evidence_matrix(
    market_data,
    drivers=None,
    premium_snapshot=None,
    battle_reference=None,
):
    return {
        "call_score": 55,
        "put_score": 10,
        "maximum_score": 100,
        "call_confidence": 55.0,
        "put_confidence": 10.0,
        "verdict": "WEAK_CALL_BIAS",
        "evidence": [
            {
                "name": "PDC",
                "side": "CALL",
                "weight": 10,
                "reason": "Above PDC",
            },
            {
                "name": "VWAP",
                "side": "CALL",
                "weight": 15,
                "reason": "Above VWAP",
            },
        ],
    }


evidence_engine.build_evidence_matrix = (
    build_evidence_matrix
)
sys.modules["evidence_engine"] = (
    evidence_engine
)


premium_engine = types.ModuleType(
    "premium_engine"
)
premium_engine.calculate_premium_snapshot = (
    lambda symbol, spot_price=None: {
        "symbol": symbol,
        "index_name": "NIFTY",
        "spot_price": 25000,
        "atm_strike": 25000,
        "expiry_date": "2026-07-28",
        "contracts": {},
        "atm_straddle": 250,
    }
)
sys.modules["premium_engine"] = (
    premium_engine
)


premium_intelligence = types.ModuleType(
    "premium_intelligence_1m"
)


class PID:
    def __init__(self, db_path):
        pass

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        pass


premium_intelligence.PremiumIntelligence1M = (
    PID
)
premium_intelligence.record_one_minute_snapshot = (
    lambda database, snapshot, **kwargs: {
        "status": "RECORDED",
        "contracts_inserted": 14,
        "straddles_inserted": 7,
    }
)
sys.modules[
    "premium_intelligence_1m"
] = premium_intelligence


behaviour_module = types.ModuleType(
    "premium_behaviour_engine"
)


class BehaviourResult:
    regime = "PREMIUM_MIGRATION_DAY"
    commander_view = "TRACK LEADER"


class BehaviourEngine:
    def __init__(self, db_path):
        pass

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        pass

    def analyse(self, symbol):
        return BehaviourResult()


behaviour_module.PremiumBehaviourEngineV3 = (
    BehaviourEngine
)
sys.modules[
    "premium_behaviour_engine"
] = behaviour_module


flow_module = types.ModuleType(
    "premium_flow_engine"
)


class FlowResult:
    dominant_side = "CALL"
    call_leader_display = (
        "OTM1 CALL — 25100 CE"
    )
    put_leader_display = (
        "ATM PUT — 25000 PE"
    )
    atm_erosion_destination = (
        "ATM CALL 25000 CE → "
        "OTM1 CALL — 25100 CE"
    )


class FlowEngine:
    def __init__(self, db_path):
        pass

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        pass

    def analyse(self, symbol):
        return FlowResult()


flow_module.PremiumFlowEngine = (
    FlowEngine
)
sys.modules[
    "premium_flow_engine"
] = flow_module


structure_module = types.ModuleType(
    "straddle_structure_engine"
)


class StructureResult:
    structure_state = (
        "EXPANSION_BREAKOUT"
    )
    straddle_bias = "LONG_STRADDLE"
    short_straddle_stance = "AVOID"


class StructureEngine:
    def __init__(self, db_path):
        pass

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        pass

    def analyse(self, symbol):
        return StructureResult()


structure_module.StraddleStructureEngine = (
    StructureEngine
)
sys.modules[
    "straddle_structure_engine"
] = structure_module


from commander_pipeline import run_pipeline


context = run_pipeline(
    "NSE:NIFTY50-INDEX",
    spot_price=25000,
    market_snapshot={
        "ltp": 25000,
        "pdc": 24900,
        "pdh": 25100,
        "pdl": 24700,
        "vwap_state": "ABOVE_VWAP",
        "ema_structure": "ABOVE_BOTH",
        "or_status": "ABOVE_ORH",
    },
)

assert context.ready is True
assert (
    context.evidence["verdict"]
    == "WEAK_CALL_BIAS"
)
assert context.evidence["score"] == 55.0
assert context.evidence["agreement"] == 2
assert (
    context.flow.call_leader_display
    == "OTM1 CALL — 25100 CE"
)

print(
    "ALL COMMANDER PIPELINE V2 "
    "TESTS PASSED"
)
