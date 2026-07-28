from threading import Lock
from time import monotonic

from fyers_client import fyers
from strike_engine import calculate_strike_universe


OPTION_CHAIN_CACHE_TTL = 2

# Request enough rows to reliably obtain ATM ±3.
OPTION_CHAIN_STRIKE_COUNT = 9

_option_chain_cache = {}
_option_chain_lock = Lock()


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def fetch_option_chain(
    symbol,
    strikecount=OPTION_CHAIN_STRIKE_COUNT,
    force_refresh=False,
):
    cache_key = (
        symbol,
        int(strikecount),
    )

    now = monotonic()

    if not force_refresh:
        with _option_chain_lock:
            cached = _option_chain_cache.get(
                cache_key
            )

            if cached:
                age = (
                    now
                    - cached["stored_at"]
                )

                if age < OPTION_CHAIN_CACHE_TTL:
                    return cached["response"]

    request_data = {
        "symbol": symbol,
        "timestamp": "",
        "strikecount": int(strikecount),
        "greeks": "1",
    }

    response = fyers.optionchain(
        data=request_data
    )

    if not isinstance(response, dict):
        raise RuntimeError(
            f"Invalid option-chain response "
            f"for {symbol}"
        )

    if response.get("s") != "ok":
        raise RuntimeError(
            f"Option chain error for {symbol}: "
            f"{response.get('message', response)}"
        )

    chain = (
        response
        .get("data", {})
        .get("optionsChain", [])
    )

    if not chain:
        raise RuntimeError(
            f"No option-chain rows received "
            f"for {symbol}"
        )

    with _option_chain_lock:
        _option_chain_cache[cache_key] = {
            "stored_at": now,
            "response": response,
        }

    return response


def parse_option(row, moneyness):
    bid = safe_float(row.get("bid"))
    ask = safe_float(row.get("ask"))
    ltp = safe_float(row.get("ltp"))

    greeks = row.get("greeks") or {}

    return {
        "symbol": row.get("symbol"),
        "strike": safe_int(
            row.get("strike_price")
        ),
        "option_type": row.get(
            "option_type"
        ),
        "moneyness": moneyness,

        "ltp": ltp,
        "change": safe_float(
            row.get("ltpch")
        ),
        "change_pct": safe_float(
            row.get("ltpchp")
        ),

        "bid": bid,
        "ask": ask,
        "spread": round(
            max(0.0, ask - bid),
            2,
        ),

        "oi": safe_int(row.get("oi")),
        "previous_oi": safe_int(
            row.get("prev_oi")
        ),
        "oi_change": safe_int(
            row.get("oich")
        ),
        "oi_change_pct": safe_float(
            row.get("oichp")
        ),
        "volume": safe_int(
            row.get("volume")
        ),

        # Hidden database fields.
        # Store these for future intelligence engines,
        # but do not print raw Greeks on the Commander terminal.
        "delta": safe_float(
            greeks.get("delta")
        ),
        "gamma": safe_float(
            greeks.get("gamma")
        ),
        "theta": safe_float(
            greeks.get("theta")
        ),
        "vega": safe_float(
            greeks.get("vega")
        ),
        "iv": safe_float(
            greeks.get("iv")
        ),
    }


def infer_strike_step(rows, atm_strike):
    """
    Infer the nearest positive strike interval directly
    from the received option-chain rows.
    """
    unique_strikes = sorted(
        {
            safe_int(row.get("strike_price"))
            for row in rows
            if (
                row.get("option_type")
                in {"CE", "PE"}
                and safe_int(
                    row.get("strike_price")
                ) > 0
            )
        }
    )

    differences = sorted(
        {
            unique_strikes[index + 1]
            - unique_strikes[index]
            for index in range(
                len(unique_strikes) - 1
            )
            if (
                unique_strikes[index + 1]
                - unique_strikes[index]
            ) > 0
        }
    )

    if differences:
        return differences[0]

    raise RuntimeError(
        f"Unable to infer strike step near ATM "
        f"{atm_strike}"
    )


def build_required_ladder(
    atm_strike,
    strike_step,
):
    """
    CE:
        ITM is below ATM, OTM is above ATM.

    PE:
        ITM is above ATM, OTM is below ATM.
    """
    required = {
        "ATM_CE": (
            atm_strike,
            "CE",
            "ATM",
        ),
        "ATM_PE": (
            atm_strike,
            "PE",
            "ATM",
        ),
    }

    for distance in range(1, 4):
        lower_strike = (
            atm_strike
            - distance * strike_step
        )
        upper_strike = (
            atm_strike
            + distance * strike_step
        )

        required[
            f"ITM{distance}_CE"
        ] = (
            lower_strike,
            "CE",
            f"ITM{distance}",
        )

        required[
            f"OTM{distance}_CE"
        ] = (
            upper_strike,
            "CE",
            f"OTM{distance}",
        )

        required[
            f"ITM{distance}_PE"
        ] = (
            upper_strike,
            "PE",
            f"ITM{distance}",
        )

        required[
            f"OTM{distance}_PE"
        ] = (
            lower_strike,
            "PE",
            f"OTM{distance}",
        )

    return required


def calculate_straddle_map(
    contracts,
):
    """
    Calculate CE + PE premium at every actual strike
    represented in the ATM ±3 ladder.
    """
    strike_map = {}

    for contract in contracts.values():
        if not contract:
            continue

        strike = contract["strike"]
        option_type = contract["option_type"]

        strike_map.setdefault(
            strike,
            {},
        )[option_type] = contract

    straddles = {}

    for strike in sorted(strike_map):
        pair = strike_map[strike]
        ce = pair.get("CE")
        pe = pair.get("PE")

        if not ce or not pe:
            continue

        straddles[strike] = {
            "strike": strike,
            "ce_symbol": ce.get("symbol"),
            "pe_symbol": pe.get("symbol"),
            "ce_ltp": ce["ltp"],
            "pe_ltp": pe["ltp"],
            "straddle": round(
                ce["ltp"] + pe["ltp"],
                2,
            ),
            "combined_oi": (
                ce["oi"] + pe["oi"]
            ),
            "combined_volume": (
                ce["volume"]
                + pe["volume"]
            ),
        }

    return straddles


def calculate_premium_snapshot(
    symbol,
    spot_price=None,
):
    """
    Returns ATM ±3 CE/PE strike ladder.

    spot_price passed:
        no extra live-quote request.

    spot_price None:
        Strike Engine uses shared live cache.
    """

    strikes = calculate_strike_universe(
        symbol=symbol,
        spot_price=spot_price,
    )

    atm = safe_int(
        strikes["atm_strike"]
    )

    response = fetch_option_chain(
        symbol=symbol,
        strikecount=(
            OPTION_CHAIN_STRIKE_COUNT
        ),
    )

    data = response.get("data", {})

    rows = data.get(
        "optionsChain",
        [],
    )

    by_key = {}

    for row in rows:
        option_type = row.get(
            "option_type"
        )

        if option_type not in {
            "CE",
            "PE",
        }:
            continue

        strike = safe_int(
            row.get("strike_price")
        )

        if strike <= 0:
            continue

        by_key[
            (
                strike,
                option_type,
            )
        ] = row

    strike_step = infer_strike_step(
        rows,
        atm,
    )

    required = build_required_ladder(
        atm_strike=atm,
        strike_step=strike_step,
    )

    contracts = {}

    for label, contract_data in (
        required.items()
    ):
        (
            strike,
            option_type,
            moneyness,
        ) = contract_data

        row = by_key.get(
            (
                strike,
                option_type,
            )
        )

        if row:
            contracts[label] = parse_option(
                row=row,
                moneyness=moneyness,
            )
        else:
            contracts[label] = None

    straddles = calculate_straddle_map(
        contracts
    )

    atm_straddle_data = straddles.get(
        atm
    )

    atm_straddle = (
        atm_straddle_data["straddle"]
        if atm_straddle_data
        else None
    )

    expiry_data = data.get(
        "expiryData",
        [],
    )

    expiry = (
        expiry_data[0]
        if expiry_data
        else {}
    )

    missing_contracts = [
        label
        for label, contract
        in contracts.items()
        if not contract
    ]

    return {
        "symbol": symbol,
        "index_name": strikes[
            "index_name"
        ],
        "spot_price": strikes[
            "spot_price"
        ],
        "atm_strike": atm,
        "strike_step": strike_step,
        "expiry_date": expiry.get(
            "date"
        ),
        "expiry_timestamp": expiry.get(
            "expiry"
        ),
        "contracts": contracts,
        "straddles": straddles,
        "atm_straddle": atm_straddle,
        "missing_contracts": (
            missing_contracts
        ),
    }


def print_contract(
    label,
    contract,
):
    if not contract:
        print(
            f"{label:<10} : "
            f"NOT AVAILABLE"
        )
        return

    print(
        f"{label:<10} : "
        f"{contract['strike']} "
        f"{contract['option_type']} | "
        f"LTP ₹{contract['ltp']:.2f} | "
        f"BID ₹{contract['bid']:.2f} | "
        f"ASK ₹{contract['ask']:.2f} | "
        f"SPR {contract['spread']:.2f} | "
        f"OI {contract['oi']} | "
        f"VOL {contract['volume']}"
    )


def print_straddle_ladder(result):
    print("-" * 100)
    print(
        "STRADDLE LADDER".center(100)
    )
    print("-" * 100)

    for strike, item in (
        result["straddles"].items()
    ):
        relation = (
            "ATM"
            if strike
            == result["atm_strike"]
            else (
                f"{(strike - result['atm_strike']) // result['strike_step']:+d}"
            )
        )

        print(
            f"STRIKE {strike:<8} "
            f"[{relation:>3}] | "
            f"CE ₹{item['ce_ltp']:<8.2f} | "
            f"PE ₹{item['pe_ltp']:<8.2f} | "
            f"STRADDLE ₹{item['straddle']:<8.2f} | "
            f"OI {item['combined_oi']} | "
            f"VOL {item['combined_volume']}"
        )


def print_snapshot(result):
    print("=" * 100)
    print(
        f"{result['index_name']} "
        f"PREMIUM RADAR — ATM ±3"
    )
    print("=" * 100)

    print(
        f"SPOT          : "
        f"{result['spot_price']:.2f}"
    )
    print(
        f"ATM STRIKE    : "
        f"{result['atm_strike']}"
    )
    print(
        f"STRIKE STEP   : "
        f"{result['strike_step']}"
    )
    print(
        f"EXPIRY        : "
        f"{result['expiry_date']}"
    )

    print("-" * 100)

    order = [
        "ITM3_CE",
        "ITM2_CE",
        "ITM1_CE",
        "ATM_CE",
        "OTM1_CE",
        "OTM2_CE",
        "OTM3_CE",
        "ITM3_PE",
        "ITM2_PE",
        "ITM1_PE",
        "ATM_PE",
        "OTM1_PE",
        "OTM2_PE",
        "OTM3_PE",
    ]

    for label in order:
        print_contract(
            label,
            result["contracts"].get(
                label
            ),
        )

    print_straddle_ladder(result)

    print("-" * 100)

    if result["atm_straddle"] is None:
        print(
            "ATM STRADDLE  : "
            "NOT AVAILABLE"
        )
    else:
        print(
            f"ATM STRADDLE  : "
            f"₹{result['atm_straddle']:.2f}"
        )

    if result["missing_contracts"]:
        print(
            "MISSING       : "
            + ", ".join(
                result[
                    "missing_contracts"
                ]
            )
        )

    print("=" * 100)


if __name__ == "__main__":
    symbols = [
        "NSE:NIFTY50-INDEX",
        "NSE:NIFTYBANK-INDEX",
        "BSE:SENSEX-INDEX",
    ]

    for symbol in symbols:
        try:
            snapshot = (
                calculate_premium_snapshot(
                    symbol
                )
            )

            print_snapshot(snapshot)

        except Exception as error:
            print("=" * 100)
            print(
                f"PREMIUM ENGINE ERROR "
                f"[{symbol}]"
            )
            print(error)
            print("=" * 100)
