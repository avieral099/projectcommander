from datetime import datetime
from zoneinfo import ZoneInfo

from market_data import get_live_quote
from price_levels import get_price_levels
from vwap_engine import calculate_vwap
from ema_engine import calculate_ema
from opening_range_engine import calculate_opening_range
from premium_engine import calculate_premium_snapshot
from driver_engine import collect_driver_data, DRIVER_SYMBOLS
from session_controller import SessionController
from live_cache import refresh_live_cache, get_live_cache_status
from evidence_engine import build_evidence_matrix, print_evidence_matrix


IST = ZoneInfo("Asia/Kolkata")

INDEX_SYMBOLS = [
    "NSE:NIFTY50-INDEX",
    "NSE:NIFTYBANK-INDEX",
    "BSE:SENSEX-INDEX",
]


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def yes_no(value):
    return "YES" if value else "NO"


def print_heading(title, width=84):
    print("\n" + "=" * width)
    print(title.center(width))
    print("=" * width)


def get_session_phase():
    controller = SessionController()
    current_time = datetime.now(IST).strftime("%H:%M")
    return current_time, controller.update(current_time)


def print_market_structure(symbol):
    quote_response = get_live_quote(symbol)

    if not quote_response:
        raise RuntimeError("Live quote unavailable")

    quote = quote_response[0].get("v", {})
    name = quote.get("short_name", symbol)

    ltp = safe_float(quote.get("lp"))
    change = safe_float(quote.get("ch"))
    change_pct = safe_float(quote.get("chp"))

    levels = get_price_levels(symbol)

    vwap = calculate_vwap(
        symbol=symbol,
        resolution="5",
    )

    ema = calculate_ema(
        symbol=symbol,
        resolution="5",
    )

    try:
        opening_range = calculate_opening_range(symbol)
    except Exception as error:
        opening_range = {
            "or_high": 0,
            "or_low": 0,
            "or_range": 0,
            "status": f"NOT AVAILABLE: {error}",
        }

    print_heading(f"{name} — MARKET STRUCTURE")

    print(f"SYMBOL                    : {symbol}")
    print(f"LTP                       : {ltp:.2f}")
    print(f"CHANGE                    : {change:+.2f}")
    print(f"CHANGE %                  : {change_pct:+.2f}%")

    print("-" * 84)

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

    today_open = levels.get("today_open")

    if today_open is None:
        print("TODAY OPEN                : MARKET CLOSED")
    else:
        print(
            f"TODAY OPEN                : "
            f"{safe_float(today_open):.2f}"
        )

    print("-" * 84)

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

    print("-" * 84)

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

    print("-" * 84)

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

    return {
        "symbol": symbol,
        "name": name,
        "ltp": ltp,
        "pdc": safe_float(
            levels.get("previous_close")
        ),
        "pdh": safe_float(
            levels.get("previous_high")
        ),
        "pdl": safe_float(
            levels.get("previous_low")
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


def print_premium_radar(symbol, spot_price):
    try:
        snapshot = calculate_premium_snapshot(
            symbol,
            spot_price=spot_price,
        )
    except Exception as error:
        print_heading(f"PREMIUM RADAR ERROR — {symbol}")
        print(error)
        return None

    contracts = snapshot.get("contracts", {})

    print_heading(
        f"{snapshot.get('index_name', symbol)} — PREMIUM RADAR"
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

    print("-" * 84)

    for label in [
        "ATM_CE",
        "ATM_PE",
        "ITM1_CE",
        "ITM1_PE",
        "OTM1_CE",
        "OTM1_PE",
    ]:
        contract = contracts.get(label)

        if not contract:
            print(f"{label:<12}: NOT AVAILABLE")
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

        print(
            f"{'':<12}  "
            f"DELTA {safe_float(contract.get('delta')):+.2f} | "
            f"GAMMA {safe_float(contract.get('gamma')):.4f} | "
            f"THETA {safe_float(contract.get('theta')):.2f} | "
            f"IV {safe_float(contract.get('iv')):.2f}"
        )


    return snapshot


def print_driver_radar():
    print_heading("INDEX DRIVER RADAR")

    try:
        drivers = collect_driver_data()
    except Exception as error:
        print(f"DRIVER ENGINE ERROR       : {error}")
        return {}

    for name, data in drivers.items():
        if data.get("error"):
            print(f"\n{name}")
            print("-" * 84)
            print(f"ERROR                     : {data['error']}")
            continue

        print(f"\n{name}")
        print("-" * 84)

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
        print(
            f"ABOVE OPENING RANGE HIGH  : "
            f"{yes_no(data.get('above_or_high'))}"
        )
        print(
            f"BELOW OPENING RANGE LOW   : "
            f"{yes_no(data.get('below_or_low'))}"
        )


    return drivers


def main():
    now = datetime.now(IST)
    current_time, phase = get_session_phase()

    # One bulk FYERS quote request for all spot and driver symbols.
    all_live_symbols = list(
        dict.fromkeys(
            INDEX_SYMBOLS
            + list(DRIVER_SYMBOLS.values())
        )
    )

    try:
        live_quote_map = refresh_live_cache(
            all_live_symbols,
            force=True,
        )
    except Exception as error:
        print("=" * 84)
        print("LIVE CACHE STARTUP ERROR")
        print("=" * 84)
        print(error)
        return

    print("\n" + "=" * 84)
    print("OPERATION COMMANDER".center(84))
    print("OPTION INTELLIGENCE & PREMIUM BEHAVIOUR TERMINAL".center(84))
    print("=" * 84)

    print(
        f"DATE                      : "
        f"{now.strftime('%Y-%m-%d')}"
    )
    print(
        f"TIME                      : "
        f"{now.strftime('%H:%M:%S')} IST"
    )
    print(f"SESSION PHASE             : {phase}")
    print(f"REFERENCE LOCK TIME       : 09:21")
    print(f"9:25 STRADDLE STATUS      : PENDING LIVE LOCK")

    market_snapshots = {}
    premium_snapshots = {}

    for symbol in INDEX_SYMBOLS:
        try:
            market_snapshots[symbol] = (
                print_market_structure(symbol)
            )
        except Exception as error:
            print_heading(
                f"MARKET STRUCTURE ERROR — {symbol}"
            )
            print(error)
            market_snapshots[symbol] = None

    for symbol in INDEX_SYMBOLS:
        quote = live_quote_map.get(symbol, {})
        spot_price = safe_float(
            quote.get("lp")
        )

        premium_snapshots[symbol] = (
            print_premium_radar(
                symbol,
                spot_price,
            )
        )

    drivers = print_driver_radar()

    # Evidence Matrix currently uses Nifty as the
    # primary directional battlefield.
    nifty_symbol = "NSE:NIFTY50-INDEX"

    nifty_market = market_snapshots.get(
        nifty_symbol
    )

    nifty_premium = premium_snapshots.get(
        nifty_symbol
    )

    evidence_result = None

    if nifty_market:
        evidence_result = build_evidence_matrix(
            market_data=nifty_market,
            drivers=drivers,
            premium_snapshot=nifty_premium,
            battle_reference=None,
        )

        print_heading(
            "NIFTY — COMMANDER EVIDENCE"
        )

        print_evidence_matrix(
            evidence_result
        )

    print_heading("COMMANDER SYSTEM STATUS")

    cache_status = get_live_cache_status()

    print("LIVE CACHE                : ONLINE")
    print(
        f"LIVE CACHE SYMBOLS        : "
        f"{cache_status.get('entries', 0)}"
    )
    print("MARKET STRUCTURE          : ONLINE")
    print("PREMIUM RADAR             : ONLINE")
    print("DRIVER RADAR              : ONLINE")
    print("SESSION CONTROLLER        : ONLINE")
    print("09:21 BATTLE REFERENCE    : AWAITING LIVE MARKET")
    print("09:25 STRADDLE REFERENCE  : AWAITING LIVE MARKET")
    if evidence_result:
        print("EVIDENCE MATRIX           : ONLINE")
        print(
            f"COMMANDER VERDICT         : "
            f"{evidence_result.get('verdict')}"
        )
        print(
            f"CALL CONFIDENCE           : "
            f"{evidence_result.get('call_confidence', 0):.2f}%"
        )
        print(
            f"PUT CONFIDENCE            : "
            f"{evidence_result.get('put_confidence', 0):.2f}%"
        )
    else:
        print("EVIDENCE MATRIX           : NOT AVAILABLE")
        print("COMMANDER VERDICT         : NOT AVAILABLE")

    print("\n" + "=" * 84)
    print("OPERATION COMMANDER — READY FOR BATTLE".center(84))
    print("=" * 84)


if __name__ == "__main__":
    main()
