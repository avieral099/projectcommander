from fyers_client import fyers
from strike_engine import calculate_strike_universe


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def fetch_option_chain(symbol, strikecount=3):
    data = {
        "symbol": symbol,
        "timestamp": "",
        "strikecount": strikecount,
        "greeks": "1",
    }

    response = fyers.optionchain(data=data)

    if response.get("s") != "ok":
        raise RuntimeError(
            f"Option chain error for {symbol}: "
            f"{response.get('message', response)}"
        )

    chain = response.get("data", {}).get(
        "optionsChain",
        []
    )

    if not chain:
        raise RuntimeError(
            f"No option-chain rows received for {symbol}"
        )

    return response


def parse_option(row, moneyness):
    bid = safe_float(row.get("bid"))
    ask = safe_float(row.get("ask"))
    ltp = safe_float(row.get("ltp"))

    greeks = row.get("greeks") or {}

    return {
        "symbol": row.get("symbol"),
        "strike": int(
            safe_float(row.get("strike_price"))
        ),
        "option_type": row.get("option_type"),
        "moneyness": moneyness,

        "ltp": ltp,
        "change": safe_float(row.get("ltpch")),
        "change_pct": safe_float(row.get("ltpchp")),

        "bid": bid,
        "ask": ask,
        "spread": round(
            max(0.0, ask - bid),
            2,
        ),

        "oi": int(safe_float(row.get("oi"))),
        "previous_oi": int(
            safe_float(row.get("prev_oi"))
        ),
        "oi_change": int(
            safe_float(row.get("oich"))
        ),
        "oi_change_pct": safe_float(
            row.get("oichp")
        ),
        "volume": int(
            safe_float(row.get("volume"))
        ),

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


def calculate_premium_snapshot(symbol):
    strikes = calculate_strike_universe(symbol)
    atm = strikes["atm_strike"]

    response = fetch_option_chain(
        symbol,
        strikecount=3,
    )

    data = response.get("data", {})
    rows = data.get("optionsChain", [])

    by_key = {}

    for row in rows:
        strike = int(
            safe_float(row.get("strike_price"))
        )
        option_type = row.get("option_type")

        if option_type in {"CE", "PE"}:
            by_key[(strike, option_type)] = row

    call_strikes = strikes["call_strikes"]
    put_strikes = strikes["put_strikes"]

    required = {
        "ATM_CE": (
            call_strikes["ATM"],
            "CE",
            "ATM",
        ),
        "ATM_PE": (
            put_strikes["ATM"],
            "PE",
            "ATM",
        ),
        "ITM1_CE": (
            call_strikes["ITM1"],
            "CE",
            "ITM1",
        ),
        "ITM1_PE": (
            put_strikes["ITM1"],
            "PE",
            "ITM1",
        ),
        "OTM1_CE": (
            call_strikes["OTM1"],
            "CE",
            "OTM1",
        ),
        "OTM1_PE": (
            put_strikes["OTM1"],
            "PE",
            "OTM1",
        ),
    }

    contracts = {}

    for label, (
        strike,
        option_type,
        moneyness,
    ) in required.items():
        row = by_key.get(
            (strike, option_type)
        )

        if row:
            contracts[label] = parse_option(
                row,
                moneyness,
            )
        else:
            contracts[label] = None

    atm_ce = contracts["ATM_CE"]
    atm_pe = contracts["ATM_PE"]

    atm_straddle = None

    if atm_ce and atm_pe:
        atm_straddle = round(
            atm_ce["ltp"] + atm_pe["ltp"],
            2,
        )

    expiry_data = data.get("expiryData", [])
    expiry = (
        expiry_data[0]
        if expiry_data
        else {}
    )

    return {
        "symbol": symbol,
        "index_name": strikes["index_name"],
        "spot_price": strikes["spot_price"],
        "atm_strike": atm,
        "expiry_date": expiry.get("date"),
        "expiry_timestamp": expiry.get("expiry"),
        "contracts": contracts,
        "atm_straddle": atm_straddle,
    }


def print_contract(label, contract):
    if not contract:
        print(f"{label:<10} : NOT AVAILABLE")
        return

    print(
        f"{label:<10} : "
        f"{contract['strike']} "
        f"{contract['option_type']} | "
        f"LTP ₹{contract['ltp']:.2f} | "
        f"BID ₹{contract['bid']:.2f} | "
        f"ASK ₹{contract['ask']:.2f} | "
        f"SPR {contract['spread']:.2f}"
    )

    print(
        f"{'':<10}   "
        f"OI {contract['oi']} | "
        f"VOL {contract['volume']} | "
        f"Δ {contract['delta']:.2f} | "
        f"Γ {contract['gamma']:.4f} | "
        f"Θ {contract['theta']:.2f} | "
        f"IV {contract['iv']:.2f}"
    )


def print_snapshot(result):
    print("=" * 90)
    print(
        f"{result['index_name']} PREMIUM RADAR"
    )
    print("=" * 90)

    print(
        f"SPOT          : "
        f"{result['spot_price']:.2f}"
    )
    print(
        f"ATM STRIKE    : "
        f"{result['atm_strike']}"
    )
    print(
        f"EXPIRY        : "
        f"{result['expiry_date']}"
    )

    print("-" * 90)

    order = [
        "ATM_CE",
        "ATM_PE",
        "ITM1_CE",
        "ITM1_PE",
        "OTM1_CE",
        "OTM1_PE",
    ]

    for label in order:
        print_contract(
            label,
            result["contracts"][label],
        )

    print("-" * 90)

    if result["atm_straddle"] is None:
        print("ATM STRADDLE  : NOT AVAILABLE")
    else:
        print(
            f"ATM STRADDLE  : "
            f"₹{result['atm_straddle']:.2f}"
        )

    print("=" * 90)


if __name__ == "__main__":
    symbols = [
        "NSE:NIFTY50-INDEX",
        "NSE:NIFTYBANK-INDEX",
        "BSE:SENSEX-INDEX",
    ]

    for symbol in symbols:
        try:
            result = calculate_premium_snapshot(
                symbol
            )
            print_snapshot(result)

        except Exception as error:
            print("=" * 90)
            print(
                f"PREMIUM ENGINE ERROR [{symbol}]"
            )
            print(error)
            print("=" * 90)
