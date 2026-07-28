import sys
import types


def module(name):
    value = types.ModuleType(name)
    sys.modules[name] = value
    return value


commander_pipeline = module(
    "commander_pipeline"
)


class Context:
    errors = {}
    evidence = {
        "verdict": "CALL_BIAS",
        "call_confidence": 75,
        "put_confidence": 10,
    }


def run_pipeline(**kwargs):
    assert (
        kwargs["premium_snapshot"][
            "atm_straddle"
        ]
        == 250
    )
    assert (
        kwargs["market_snapshot"][
            "vwap_state"
        ]
        == "ABOVE_VWAP"
    )
    return Context()


commander_pipeline.run_pipeline = (
    run_pipeline
)


commander_terminal = module(
    "commander_terminal"
)
commander_terminal.print_commander_context = (
    lambda context: None
)


driver_engine = module(
    "driver_engine"
)
driver_engine.DRIVER_SYMBOLS = {
    "DRIVER": "NSE:DRIVER-EQ"
}
driver_engine.collect_driver_data = (
    lambda: {}
)


ema_engine = module(
    "ema_engine"
)
ema_engine.calculate_ema = (
    lambda **kwargs: {
        "ema75_high": 10,
        "ema75_low": 8,
        "ema75_high_relation": "ABOVE",
        "ema75_low_relation": "ABOVE",
        "structure_state": "ABOVE_BOTH",
    }
)


live_cache = module(
    "live_cache"
)
live_cache.refresh_live_cache = (
    lambda symbols, force=False: {
        symbol: {"lp": 100}
        for symbol in symbols
    }
)
live_cache.get_live_cache_status = (
    lambda: {"entries": 4}
)


market_data = module(
    "market_data"
)
market_data.get_live_quote = (
    lambda symbol: [
        {
            "v": {
                "short_name": symbol,
                "lp": 100,
                "ch": 1,
                "chp": 1,
            }
        }
    ]
)


opening_range = module(
    "opening_range_engine"
)
opening_range.calculate_opening_range = (
    lambda symbol: {
        "or_high": 99,
        "or_low": 95,
        "or_range": 4,
        "status": "ABOVE_ORH",
    }
)


premium_engine = module(
    "premium_engine"
)
premium_engine.calculate_premium_snapshot = (
    lambda symbol, spot_price=None: {
        "index_name": symbol,
        "spot_price": spot_price,
        "atm_strike": 100,
        "expiry_date": "2026-07-28",
        "atm_straddle": 250,
        "contracts": {},
    }
)


price_levels = module(
    "price_levels"
)
price_levels.get_price_levels = (
    lambda symbol: {
        "previous_day_date": "2026-07-24",
        "previous_open": 95,
        "previous_high": 105,
        "previous_low": 90,
        "previous_close": 98,
        "today_open": None,
    }
)


session_controller = module(
    "session_controller"
)


class SessionController:
    def update(self, current_time):
        return "MARKET_CLOSED"


session_controller.SessionController = (
    SessionController
)


vwap_engine = module(
    "vwap_engine"
)
vwap_engine.calculate_vwap = (
    lambda **kwargs: {
        "vwap": 97,
        "state": "ABOVE_VWAP",
        "percentage_distance": 3,
    }
)


import dashboard


dashboard.main()

print(
    "ALL DASHBOARD COMMANDER "
    "INTEGRATION TESTS PASSED"
)
