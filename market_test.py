# ============================================================
# PROJECT: OPERATION COMMANDER
# FILE: market_test.py
# PURPOSE: VERIFY FYERS LIVE QUOTES
# ============================================================

from pathlib import Path
from pprint import pprint

from fyers_apiv3 import fyersModel
from config import APP_ID


# ============================================================
# LOAD FRESH ACCESS TOKEN
# ============================================================

TOKEN_FILE = Path(__file__).resolve().parent / "access_token.txt"

if not TOKEN_FILE.exists():
    print("ERROR: access_token.txt not found")
    print("Run fyers_auth.py and generate_token.py first.")
    raise SystemExit(1)

access_token = TOKEN_FILE.read_text(encoding="utf-8").strip()

if not access_token:
    print("ERROR: access_token.txt is empty")
    raise SystemExit(1)


# ============================================================
# CREATE FYERS CLIENT
# ============================================================

fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=access_token,
    is_async=False,
    log_path="",
)


# ============================================================
# SYMBOLS
# ============================================================

symbols = [
    "NSE:NIFTY50-INDEX",
    "NSE:NIFTYBANK-INDEX",
    "BSE:SENSEX-INDEX",
]

request_data = {
    "symbols": ",".join(symbols)
}


# ============================================================
# REQUEST LIVE QUOTES
# ============================================================

response = fyers.quotes(data=request_data)


# ============================================================
# HEADER
# ============================================================

print("=" * 74)
print("                       PROJECT COMMANDER")
print("=" * 74)


# ============================================================
# RESPONSE VALIDATION
# ============================================================

if not isinstance(response, dict):
    print("INVALID FYERS RESPONSE")
    pprint(response)
    raise SystemExit(1)

if response.get("s") != "ok":
    print("FYERS LIVE QUOTE REQUEST FAILED")
    print("-" * 74)
    print(f"STATUS  : {response.get('s', 'UNKNOWN')}")
    print(f"CODE    : {response.get('code', 'UNKNOWN')}")
    print(f"MESSAGE : {response.get('message', 'UNKNOWN ERROR')}")
    print("-" * 74)
    pprint(response)
    raise SystemExit(1)

quote_items = response.get("d")

if not isinstance(quote_items, list) or not quote_items:
    print("NO QUOTE DATA RECEIVED")
    print("-" * 74)
    pprint(response)
    raise SystemExit(1)


# ============================================================
# DISPLAY QUOTES
# ============================================================

for item in quote_items:
    quote = item.get("v", {})

    symbol = (
        quote.get("short_name")
        or quote.get("symbol")
        or item.get("n")
        or "UNKNOWN"
    )

    ltp = quote.get("lp", "N/A")
    change = quote.get("ch", "N/A")
    change_percent = quote.get("chp", "N/A")

    print()
    print(f"SYMBOL      : {symbol}")
    print(f"LTP         : {ltp}")
    print(f"CHANGE      : {change}")
    print(f"CHANGE %    : {change_percent}")
    print("-" * 74)


print()
print("=" * 74)
print("              FYERS LIVE MARKET CONNECTION: ONLINE")
print("=" * 74)