
from datetime import datetime
import os
import time
from zoneinfo import ZoneInfo

from commander_final_layer import (
    apply_final_layer,
    print_final_layer,
)
from commander_pipeline import run_pipeline
from commander_terminal import (
    print_commander_context,
)
from driver_engine import (
    DRIVER_SYMBOLS,
    collect_driver_data,
)
from ema_engine import calculate_ema
from live_cache import (
    get_live_cache_status,
    refresh_live_cache,
)
from market_data import get_live_quote
from opening_range_engine import (
    calculate_opening_range,
)
from premium_engine import (
    calculate_premium_snapshot,
)
from premium_intelligence_1m import PremiumIntelligence1M
from price_levels import get_price_levels
from session_controller import SessionController
from vwap_engine import calculate_vwap


IST = ZoneInfo("Asia/Kolkata")
WIDTH = 92

INDEX_SYMBOLS = [
    "NSE:NIFTY50-INDEX",
    "NSE:NIFTYBANK-INDEX",
    "BSE:SENSEX-INDEX",
]

NIFTY_SYMBOL = "NSE:NIFTY50-INDEX"


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def yes_no(value):
    return "YES" if value else "NO"


def progress_bar(percent, width=28):
    percent = max(
        0.0,
        min(
            safe_float(percent),
            100.0,
        ),
    )

    filled = round(
        (percent / 100.0) * width
    )

    return (
        "█" * filled
        + "░" * (width - filled)
    )


def print_heading(
    title,
    width=WIDTH,
    char="=",
):
    print("\n" + char * width)
    print(title.center(width))
    print(char * width)


def print_subheading(
    title,
    width=WIDTH,
):
    print(
        "\n"
        + f" {title} ".center(
            width,
            "-",
        )
    )


def get_session_phase():
    controller = SessionController()

    current_time = datetime.now(
        IST
    ).strftime("%H:%M")

    return (
        current_time,
        controller.update(
            current_time
        ),
    )


def get_market_mission_status(phase):
    phase_text = str(
        phase
    ).upper()

    if "PRE" in phase_text:
        return (
            "SYSTEMS ARMED — "
            "AWAITING OPENING BELL"
        )

    if any(
        word in phase_text
        for word in (
            "OPEN",
            "LIVE",
            "MARKET",
        )
    ):
        return (
            "LIVE BATTLEFIELD — "
            "SCANNING FOR EDGE"
        )

    if any(
        word in phase_text
        for word in (
            "CLOSED",
            "POST",
        )
    ):
        return (
            "MARKET CLOSED — "
            "INTELLIGENCE REVIEW MODE"
        )

    return "COMMAND CENTRE ONLINE"


def get_verdict_order(
    verdict,
    call_confidence,
    put_confidence,
):
    verdict_text = str(
        verdict or "NO_BIAS"
    ).upper()

    if "CALL" in verdict_text:
        confidence = safe_float(
            call_confidence
        )
        side = "CALL"

    elif "PUT" in verdict_text:
        confidence = safe_float(
            put_confidence
        )
        side = "PUT"

    else:
        confidence = max(
            safe_float(
                call_confidence
            ),
            safe_float(
                put_confidence
            ),
        )
        side = "NEUTRAL"

    if confidence >= 85:
        return (
            "TARGET ACQUIRED",
            (
                f"ENGAGE {side} WITH "
                f"DEFINED PREMIUM RISK"
            ),
        )

    if confidence >= 70:
        return (
            "HIGH-CONVICTION WATCH",
            (
                f"{side} BIAS — WAIT FOR "
                f"EXECUTION TRIGGER"
            ),
        )

    if confidence >= 55:
        return (
            "SNIPER MODE",
            (
                f"{side} BIAS — "
                f"CONFIRMATION REQUIRED"
            ),
        )

    return (
        "HOLD YOUR FIRE",
        (
            "THE MARKET HAS NOT "
            "EARNED YOUR CAPITAL"
        ),
    )


def print_system_health(statuses):
    online = []
    pending = []
    offline = []
    information = []

    for name, value in statuses.items():
        text = str(value).upper()

        if (
            isinstance(
                value,
                (int, float),
            )
            or text.replace(
                ".",
                "",
                1,
            ).isdigit()
        ):
            information.append(
                (
                    name,
                    value,
                )
            )

        elif any(
            word in text
            for word in (
                "AWAITING",
                "PENDING",
                "WAITING",
            )
        ):
            pending.append(
                (
                    name,
                    value,
                )
            )

        elif any(
            word in text
            for word in (
                "ERROR",
                "OFFLINE",
                "FAILED",
                "DEGRADED",
            )
        ):
            offline.append(
                (
                    name,
                    value,
                )
            )

        else:
            online.append(
                (
                    name,
                    value,
                )
            )

    total = (
        len(online)
        + len(pending)
        + len(offline)
    )

    health = round(
        (
            len(online)
            / max(total, 1)
        )
        * 100
    )

    print_heading(
        "COMMANDER SYSTEM HEALTH"
    )

    print(
        f"HEALTH                    : "
        f"{progress_bar(health, 30)} "
        f"{health:>3}%"
    )
    print(
        f"ONLINE                    : "
        f"{len(online):>2}   "
        f"PENDING : {len(pending):>2}   "
        f"OFFLINE : {len(offline):>2}"
    )

    if information:
        print_subheading(
            "INFORMATION"
        )

        for name, value in information:
            print(
                f"{name:<28}: {value}"
            )

    if pending:
        print_subheading(
            "PENDING"
        )

        for name, value in pending:
            print(
                f"○ {name:<26}: {value}"
            )

    if offline:
        print_subheading(
            "ATTENTION REQUIRED"
        )

        for name, value in offline:
            print(
                f"× {name:<26}: {value}"
            )


def print_market_structure(symbol):
    quote_response = get_live_quote(
        symbol
    )

    if not quote_response:
        raise RuntimeError(
            "Live quote unavailable"
        )

    quote = quote_response[0].get(
        "v",
        {},
    )

    name = quote.get(
        "short_name",
        symbol,
    )

    ltp = safe_float(
        quote.get("lp")
    )
    change = safe_float(
        quote.get("ch")
    )
    change_pct = safe_float(
        quote.get("chp")
    )

    levels = get_price_levels(
        symbol
    )

    vwap = calculate_vwap(
        symbol=symbol,
        resolution="5",
    )

    ema = calculate_ema(
        symbol=symbol,
        resolution="5",
    )

    try:
        opening_range = (
            calculate_opening_range(
                symbol
            )
        )

    except Exception as error:
        opening_range = {
            "or_high": 0,
            "or_low": 0,
            "or_range": 0,
            "status": (
                f"NOT AVAILABLE: "
                f"{error}"
            ),
        }

    print_heading(
        f"{name} — MARKET STRUCTURE"
    )

    print(
        f"SYMBOL                    : "
        f"{symbol}"
    )
    print(
        f"LTP                       : "
        f"{ltp:.2f}"
    )
    print(
        f"CHANGE                    : "
        f"{change:+.2f}"
    )
    print(
        f"CHANGE %                  : "
        f"{change_pct:+.2f}%"
    )

    print("-" * WIDTH)

    print(
        f"PREVIOUS DAY DATE         : "
        f"{levels.get('previous_day_date', 'UNKNOWN')}"
    )
    print(
        f"PREVIOUS DAY OPEN         : "
        f"{safe_float(levels.get('previous_open')):.2f}"
    )
    print(
        f"PREVIOUS DAY HIGH         : "
        f"{safe_float(levels.get('previous_high')):.2f}"
    )
    print(
        f"PREVIOUS DAY LOW          : "
        f"{safe_float(levels.get('previous_low')):.2f}"
    )
    print(
        f"PREVIOUS DAY CLOSE        : "
        f"{safe_float(levels.get('previous_close')):.2f}"
    )

    today_open = levels.get(
        "today_open"
    )

    if today_open is None:
        print(
            "TODAY OPEN                : "
            "MARKET CLOSED"
        )
    else:
        print(
            f"TODAY OPEN                : "
            f"{safe_float(today_open):.2f}"
        )

    print("-" * WIDTH)

    print(
        f"VWAP                      : "
        f"{safe_float(vwap.get('vwap')):.2f}"
    )
    print(
        f"VWAP STATE                : "
        f"{vwap.get('state', 'UNKNOWN')}"
    )
    print(
        f"VWAP DISTANCE             : "
        f"{safe_float(vwap.get('percentage_distance')):+.2f}%"
    )

    print("-" * WIDTH)

    print(
        f"EMA75 HIGH                : "
        f"{safe_float(ema.get('ema75_high')):.2f}"
    )
    print(
        f"EMA75 HIGH RELATION       : "
        f"{ema.get('ema75_high_relation', 'UNKNOWN')}"
    )
    print(
        f"EMA75 LOW                 : "
        f"{safe_float(ema.get('ema75_low')):.2f}"
    )
    print(
        f"EMA75 LOW RELATION        : "
        f"{ema.get('ema75_low_relation', 'UNKNOWN')}"
    )
    print(
        f"EMA STRUCTURE             : "
        f"{ema.get('structure_state', 'UNKNOWN')}"
    )

    print("-" * WIDTH)

    print(
        f"OPENING RANGE HIGH        : "
        f"{safe_float(opening_range.get('or_high')):.2f}"
    )
    print(
        f"OPENING RANGE LOW         : "
        f"{safe_float(opening_range.get('or_low')):.2f}"
    )
    print(
        f"OPENING RANGE             : "
        f"{safe_float(opening_range.get('or_range')):.2f}"
    )
    print(
        f"OPENING RANGE STATUS      : "
        f"{opening_range.get('status', 'UNKNOWN')}"
    )

    pdc = safe_float(
        levels.get(
            "previous_close"
        )
    )

    return {
        "symbol": symbol,
        "name": name,
        "ltp": ltp,
        "change_pct": change_pct,
        "pdc": pdc,
        "pdh": safe_float(
            levels.get(
                "previous_high"
            )
        ),
        "pdl": safe_float(
            levels.get(
                "previous_low"
            )
        ),
        "above_pdc": (
            pdc > 0
            and ltp > pdc
        ),
        "vwap_state": vwap.get(
            "state",
            "UNKNOWN",
        ),
        "ema_structure": ema.get(
            "structure_state",
            "UNKNOWN",
        ),
        "or_status": opening_range.get(
            "status",
            "UNKNOWN",
        ),
    }



def get_reference_lock(
    symbol,
    expiry_date,
):
    trading_date = datetime.now(
        IST
    ).strftime("%Y-%m-%d")

    with PremiumIntelligence1M() as database:
        straddle_lock = database.reference(
            trading_date,
            "STRADDLE_0925",
            symbol,
            expiry_date,
        )

        if straddle_lock:
            return straddle_lock

        return database.reference(
            trading_date,
            "BATTLE_0921",
            symbol,
            expiry_date,
        )


def print_premium_radar(
    symbol,
    spot_price,
):
    try:
        snapshot = (
            calculate_premium_snapshot(
                symbol,
                spot_price=spot_price,
            )
        )

        lock = get_reference_lock(
            symbol,
            snapshot.get(
                "expiry_date"
            ),
        )

        if lock:
            snapshot = (
                calculate_premium_snapshot(
                    symbol,
                    spot_price=spot_price,
                    fixed_atm=lock.get(
                        "atm_strike"
                    ),
                    fixed_expiry=lock.get(
                        "expiry_date"
                    ),
                )
            )

    except Exception as error:
        print_heading(
            f"PREMIUM RADAR ERROR — "
            f"{symbol}"
        )
        print(error)
        return None

    contracts = snapshot.get(
        "contracts",
        {},
    )

    print_heading(
        f"{snapshot.get('index_name', symbol)} "
        f"— PREMIUM RADAR"
    )

    print(
        f"SPOT                      : "
        f"{safe_float(snapshot.get('spot_price')):.2f}"
    )
    print(
        f"ATM STRIKE                : "
        f"{snapshot.get('atm_strike', 'UNKNOWN')}"
    )
    print(
        f"EXPIRY                    : "
        f"{snapshot.get('expiry_date', 'UNKNOWN')}"
    )
    print(
        f"ATM STRADDLE              : "
        f"₹{safe_float(snapshot.get('atm_straddle')):.2f}"
    )

    print("-" * WIDTH)

    for label in (
        "ATM_CE",
        "ATM_PE",
        "ITM1_CE",
        "ITM1_PE",
        "OTM1_CE",
        "OTM1_PE",
    ):
        contract = contracts.get(
            label
        )

        if not contract:
            print(
                f"{label:<12}: "
                f"NOT AVAILABLE"
            )
            continue

        print(
            f"{label:<12}: "
            f"{contract.get('strike')} "
            f"{contract.get('option_type')} | "
            f"LTP ₹{safe_float(contract.get('ltp')):.2f} | "
            f"BID ₹{safe_float(contract.get('bid')):.2f} | "
            f"ASK ₹{safe_float(contract.get('ask')):.2f} | "
            f"OI {contract.get('oi', 0)} | "
            f"VOL {contract.get('volume', 0)}"
        )

    return snapshot


def print_driver_radar():
    print_heading(
        "INDEX DRIVER RADAR"
    )

    try:
        drivers = (
            collect_driver_data()
        )

    except Exception as error:
        print(
            f"DRIVER ENGINE ERROR       : "
            f"{error}"
        )
        return {}

    for name, data in drivers.items():
        if data.get("error"):
            print(f"\n{name}")
            print("-" * WIDTH)
            print(
                f"ERROR                     : "
                f"{data['error']}"
            )
            continue

        print(f"\n{name}")
        print("-" * WIDTH)

        print(
            f"LTP                       : "
            f"{safe_float(data.get('ltp')):.2f}"
        )
        print(
            f"ABOVE PDC                 : "
            f"{yes_no(data.get('above_pdc'))}"
        )
        print(
            f"ABOVE PDH                 : "
            f"{yes_no(data.get('above_pdh'))}"
        )
        print(
            f"BELOW PDL                 : "
            f"{yes_no(data.get('below_pdl'))}"
        )
        print(
            f"VWAP STATE                : "
            f"{data.get('vwap_state', 'UNKNOWN')}"
        )
        print(
            f"EMA STRUCTURE             : "
            f"{data.get('ema_structure', 'UNKNOWN')}"
        )
        print(
            f"OPENING RANGE STATUS      : "
            f"{data.get('or_status', 'UNKNOWN')}"
        )

    return drivers



def print_key_value(label, value, label_width=26):
    print(f"{label:<{label_width}} : {value}")


def render_commander_header(now, phase):
    print("\n" + "=" * WIDTH)
    print("OPERATION COMMANDER".center(WIDTH))
    print("OPTION INTELLIGENCE & PREMIUM BEHAVIOUR TERMINAL".center(WIDTH))
    print("=" * WIDTH)

    print_key_value("DATE", now.strftime("%Y-%m-%d"))
    print_key_value("TIME", f"{now.strftime('%H:%M:%S')} IST")
    print_key_value("SESSION PHASE", phase)
    print_key_value("MISSION STATUS", get_market_mission_status(phase))
    print_key_value("09:21 REFERENCE", "ENGINE CONTROLLED")
    print_key_value("09:25 STRADDLE", "ENGINE CONTROLLED")


def render_commander_footer(verdict_status, final_order):
    print("\n" + "=" * WIDTH)
    print("COMMANDER SUMMARY".center(WIDTH))
    print("=" * WIDTH)
    print_key_value("VERDICT", verdict_status)
    print_key_value("ORDER", final_order)
    print("=" * WIDTH)




def render_live_status_strip(
    *,
    cache_status,
    commander_contexts,
    evidence_result,
    pipeline_errors,
):
    cache_online = (
        safe_float(
            cache_status.get(
                "entries",
                0,
            )
        ) > 0
    )

    premium_online = bool(
        commander_contexts
    )

    evidence_score = safe_float(
        evidence_result.get(
            "score",
            evidence_result.get(
                "evidence_score",
                0,
            ),
        )
        if evidence_result
        else 0
    )

    decision_ready = any(
        getattr(
            getattr(
                context,
                "decision",
                None,
            ),
            "action",
            "NO_TRADE",
        )
        != "NO_TRADE"
        for context in commander_contexts.values()
    )

    print("\n" + "=" * WIDTH)
    print(
        " | ".join(
            (
                "LIVE",
                (
                    "CACHE OK"
                    if cache_online
                    else "CACHE DOWN"
                ),
                (
                    "PREMIUM OK"
                    if premium_online
                    else "PREMIUM DOWN"
                ),
                f"EVIDENCE {evidence_score:.0f}%",
                (
                    "DECISION READY"
                    if decision_ready
                    else "DECISION WAIT"
                ),
                f"ERRORS {pipeline_errors}",
            )
        ).center(WIDTH)
    )
    print("=" * WIDTH)

def render_market_overview(snapshots):
    print_heading("MARKET STRUCTURE — COMPACT VIEW")

    print(
        f"{'INDEX':<12}"
        f"{'LTP':>11}"
        f"{'CHANGE %':>11}"
        f"{'VWAP':>18}"
        f"{'EMA75':>18}"
        f"{'OPENING RANGE':>20}"
    )
    print("-" * WIDTH)

    for symbol, data in snapshots.items():
        if not data:
            continue

        name = (
            symbol.replace("NSE:", "")
            .replace("BSE:", "")
            .replace("-INDEX", "")
        )

        print(
            f"{name:<12}"
            f"{safe_float(data.get('ltp')):>11.2f}"
            f"{safe_float(data.get('change_pct')):>+10.2f}%"
            f"{str(data.get('vwap_state', 'UNKNOWN')):>18}"
            f"{str(data.get('ema_structure', 'UNKNOWN')):>18}"
            f"{str(data.get('or_status', 'UNKNOWN')):>20}"
        )


def render_premium_overview(snapshots):
    print_heading("PREMIUM RADAR — COMPACT VIEW")

    print(
        f"{'INDEX':<12}"
        f"{'SPOT':>12}"
        f"{'ATM':>10}"
        f"{'STRADDLE':>14}"
        f"{'EXPIRY':>16}"
    )
    print("-" * WIDTH)

    for symbol, data in snapshots.items():
        if not data:
            continue

        name = str(
            data.get(
                "index_name",
                symbol,
            )
        )

        print(
            f"{name:<12}"
            f"{safe_float(data.get('spot_price')):>12.2f}"
            f"{str(data.get('atm_strike', 'UNKNOWN')):>10}"
            f"{safe_float(data.get('atm_straddle')):>13.2f}"
            f"{str(data.get('expiry_date', 'UNKNOWN')):>16}"
        )


def render_driver_overview(drivers):
    print_heading("INDEX DRIVER RADAR — COMPACT VIEW")

    print(
        f"{'DRIVER':<14}"
        f"{'LTP':>11} "
        f"{'VWAP':>16} "
        f"{'EMA75':>27} "
        f"{'OPENING RANGE':>18}"
    )
    print("-" * WIDTH)

    for name, data in drivers.items():
        if data.get("error"):
            print(
                f"{name:<14}"
                f"{'ERROR':>11}"
                f"{str(data.get('error')):>60}"
            )
            continue

        print(
            f"{name:<14}"
            f"{safe_float(data.get('ltp')):>11.2f} "
            f"{str(data.get('vwap_state', 'UNKNOWN')):>16} "
            f"{str(data.get('ema_structure', 'UNKNOWN')):>27} "
            f"{str(data.get('or_status', 'UNKNOWN')):>18}"
        )


def render_pipeline_overview(contexts):
    print_heading("COMMANDER PIPELINE — COMPACT VIEW")

    print(
        f"{'INDEX':<12}"
        f"{'VERDICT':>20}"
        f"{'CALL %':>10}"
        f"{'PUT %':>10}"
        f"{'ACTION':>14}"
        f"{'SIDE':>10}"
        f"{'CONVICTION':>14}"
    )
    print("-" * WIDTH)

    for symbol, context in contexts.items():
        evidence = getattr(
            context,
            "evidence",
            {},
        ) or {}

        decision = getattr(
            context,
            "decision",
            None,
        )

        name = (
            symbol.replace("NSE:", "")
            .replace("BSE:", "")
            .replace("-INDEX", "")
        )

        print(
            f"{name:<12}"
            f"{str(evidence.get('verdict', 'UNKNOWN')):>20}"
            f"{safe_float(evidence.get('call_confidence')):>9.2f}%"
            f"{safe_float(evidence.get('put_confidence')):>9.2f}%"
            f"{str(getattr(decision, 'action', 'NO_TRADE')):>14}"
            f"{str(getattr(decision, 'side', 'NONE')):>10}"
            f"{safe_float(getattr(decision, 'conviction', 0)):>13.2f}"
        )

def main():
    import io
    from contextlib import redirect_stdout

    now = datetime.now(IST)
    _, phase = get_session_phase()

    all_live_symbols = list(
        dict.fromkeys(
            INDEX_SYMBOLS
            + list(
                DRIVER_SYMBOLS.values()
            )
        )
    )

    try:
        live_quote_map = (
            refresh_live_cache(
                all_live_symbols,
                force=True,
            )
        )

    except Exception as error:
        print("=" * WIDTH)
        print(
            "LIVE CACHE STARTUP ERROR"
        )
        print("=" * WIDTH)
        print(error)
        return

    render_commander_header(
        now,
        phase,
    )

    market_snapshots = {}
    premium_snapshots = {}

    for symbol in INDEX_SYMBOLS:
        try:
            with redirect_stdout(
                io.StringIO()
            ):
                market_snapshots[symbol] = (
                    print_market_structure(
                        symbol
                    )
                )

        except Exception as error:
            print_heading(
                f"MARKET STRUCTURE ERROR — "
                f"{symbol}"
            )
            print(error)
            market_snapshots[symbol] = (
                None
            )

    for symbol in INDEX_SYMBOLS:
        quote = live_quote_map.get(
            symbol,
            {},
        )

        spot_price = safe_float(
            quote.get("lp")
        )

        with redirect_stdout(
            io.StringIO()
        ):
            premium_snapshots[symbol] = (
                print_premium_radar(
                    symbol,
                    spot_price,
                )
            )

    with redirect_stdout(
        io.StringIO()
    ):
        drivers = print_driver_radar()

    render_market_overview(
        market_snapshots
    )
    render_premium_overview(
        premium_snapshots
    )
    render_driver_overview(
        drivers
    )

    commander_contexts = {}

    for symbol in INDEX_SYMBOLS:
        market_snapshot = (
            market_snapshots.get(
                symbol
            )
        )

        premium_snapshot = (
            premium_snapshots.get(
                symbol
            )
        )

        if (
            not market_snapshot
            or not premium_snapshot
        ):
            continue

        symbol_drivers = (
            drivers
            if symbol == NIFTY_SYMBOL
            else None
        )

        context = run_pipeline(
            symbol=symbol,
            spot_price=safe_float(
                market_snapshot.get(
                    "ltp"
                )
            ),
            premium_snapshot=(
                premium_snapshot
            ),
            market_snapshot=(
                market_snapshot
            ),
            drivers=symbol_drivers,
            battle_reference=None,
        )

        commander_contexts[
            symbol
        ] = context

        with redirect_stdout(
            io.StringIO()
        ):
            print_commander_context(
                context
            )

        try:
            apply_final_layer(
                context,
                market_snapshot=(
                    market_snapshot
                ),
            )

            with redirect_stdout(
                io.StringIO()
            ):
                print_final_layer(
                    context
                )

        except Exception as error:
            context.set_error(
                "commander_final_layer",
                error,
            )

            print_heading(
                f"FINAL LAYER ERROR — "
                f"{symbol}"
            )
            print(error)

    nifty_context = (
        commander_contexts.get(
            NIFTY_SYMBOL
        )
    )

    evidence_result = (
        nifty_context.evidence
        if nifty_context
        else None
    )

    verdict_status = (
        "NOT AVAILABLE"
    )

    final_order = (
        "NO DEPLOYMENT AUTHORISED"
    )

    if evidence_result:
        verdict_status, final_order = (
            get_verdict_order(
                evidence_result.get(
                    "verdict"
                ),
                evidence_result.get(
                    "call_confidence",
                    0,
                ),
                evidence_result.get(
                    "put_confidence",
                    0,
                ),
            )
        )

    cache_status = (
        get_live_cache_status()
    )

    pipeline_errors = sum(
        len(context.errors)
        for context in (
            commander_contexts.values()
        )
    )

    render_live_status_strip(
        cache_status=cache_status,
        commander_contexts=commander_contexts,
        evidence_result=evidence_result,
        pipeline_errors=pipeline_errors,
    )

    system_statuses = {
        "LIVE CACHE": "ONLINE",
        "LIVE CACHE SYMBOLS": (
            cache_status.get(
                "entries",
                0,
            )
        ),
        "MARKET STRUCTURE": (
            "ONLINE"
        ),
        "PREMIUM RADAR": "ONLINE",
        "PREMIUM RECORDER": (
            "ONLINE"
            if commander_contexts
            else "NOT AVAILABLE"
        ),
        "PREMIUM BEHAVIOUR": (
            "ONLINE"
            if commander_contexts
            else "NOT AVAILABLE"
        ),
        "PREMIUM FLOW": (
            "ONLINE"
            if commander_contexts
            else "NOT AVAILABLE"
        ),
        "STRADDLE STRUCTURE": (
            "ONLINE"
            if commander_contexts
            else "NOT AVAILABLE"
        ),
        "BATTLE ENGINE": (
            "ONLINE"
            if commander_contexts
            else "NOT AVAILABLE"
        ),
        "EVIDENCE MATRIX": (
            "ONLINE"
            if evidence_result
            else "NOT AVAILABLE"
        ),
        "REFERENCE LOCK ENGINE": (
            "ONLINE"
            if commander_contexts
            else "NOT AVAILABLE"
        ),
        "DECISION ENGINE": (
            "ONLINE"
            if commander_contexts
            else "NOT AVAILABLE"
        ),
        "PIPELINE ERRORS": (
            pipeline_errors
        ),
        "DRIVER RADAR": "ONLINE",
        "SESSION CONTROLLER": (
            "ONLINE"
        ),
        "09:21 BATTLE REFERENCE": (
            "AWAITING / LOCKED BY ENGINE"
        ),
        "09:25 STRADDLE REFERENCE": (
            "AWAITING / LOCKED BY ENGINE"
        ),
        "COMMANDER VERDICT": (
            evidence_result.get(
                "verdict"
            )
            if evidence_result
            else "NOT AVAILABLE"
        ),
    }

    render_pipeline_overview(
        commander_contexts
    )

    print_system_health(
        system_statuses
    )

    render_commander_footer(
        verdict_status,
        final_order,
    )


if __name__ == "__main__":
    while True:
        os.system("clear")
        main()
        time.sleep(5)
