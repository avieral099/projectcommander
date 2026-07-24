# Import Required Libraries

from market_data  import get_live_quote
from price_levels import previous_high
from price_levels import previous_low
from price_levels import previous_close

from vwap_engine  import vwap
from ema_engine   import ema20
from ema_engine   import ema50
from ema_engine   import ema100
from ema_engine   import ema200


# Fetch Live Market Data

quotes = get_live_quote(
    "NSE:NIFTY50-INDEX,NSE:NIFTYBANK-INDEX,BSE:SENSEX-INDEX"
)


# Check Data

if not quotes:

    print("=" * 65)
    print("LIVE MARKET DATA NOT AVAILABLE")
    print("=" * 65)

    exit()


# Print Dashboard Header

print("=" * 65)
print("                    PROJECT COMMANDER")
print("=" * 65)


# Print Live Data

for item in quotes:


    quote = item["v"]

    print(f"{quote['short_name']}")
    print(f"LTP       : {quote['lp']}")
    print(f"CHANGE    : {quote['ch']}")
    print(f"CHANGE %  : {quote['chp']}")
    print(f"PDH       : {previous_high}")
    print(f"PDL       : {previous_low}")
    print(f"PDC       : {previous_close}")
    print(f"VWAP      : {vwap:.2f}")
    
    print(f"EMA 20    : {ema20:.2f}")
    print(f"EMA 50    : {ema50:.2f}")
    print(f"EMA 100   : {ema100:.2f}")
    print(f"EMA 200   : {ema200:.2f}")
    
    print("-" * 65)