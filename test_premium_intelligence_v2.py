from pathlib import Path
from tempfile import TemporaryDirectory
from premium_intelligence_1m import PremiumIntelligence1M, record_one_minute_snapshot

def make_contract(label,strike,option_type,ltp):
    return {
        "symbol": label, "strike": strike, "option_type": option_type,
        "ltp": ltp, "change": -5, "change_pct": 0,
        "bid": ltp-.5, "ask": ltp+.5, "volume": 1000, "oi": 5000,
        "iv": 14, "delta": .5 if option_type=="CE" else -.5,
        "gamma": .002, "theta": -7, "vega": 4,
    }

def snapshot(atm=25000, spot=25010, ce=130, pe=120):
    d = {
        "ITM3_CE":(atm-300,"CE",300),"ITM2_CE":(atm-200,"CE",240),
        "ITM1_CE":(atm-100,"CE",180),"ATM_CE":(atm,"CE",ce),
        "OTM1_CE":(atm+100,"CE",85),"OTM2_CE":(atm+200,"CE",55),
        "OTM3_CE":(atm+300,"CE",32),"ITM3_PE":(atm+300,"PE",295),
        "ITM2_PE":(atm+200,"PE",235),"ITM1_PE":(atm+100,"PE",175),
        "ATM_PE":(atm,"PE",pe),"OTM1_PE":(atm-100,"PE",82),
        "OTM2_PE":(atm-200,"PE",52),"OTM3_PE":(atm-300,"PE",30),
    }
    return {
        "index_name":"NIFTY","expiry_date":"2026-07-28",
        "spot_price":spot,"atm_strike":atm,"strike_step":100,
        "contracts":{
            label:make_contract(label,strike,opt,ltp)
            for label,(strike,opt,ltp) in d.items()
        }
    }

with TemporaryDirectory() as tmp:
    with PremiumIntelligence1M(Path(tmp)/"pid.db") as db:
        first = record_one_minute_snapshot(
            db,snapshot(),index_symbol="NSE:NIFTY50-INDEX",
            timestamp="2026-07-27T09:21:00+05:30"
        )
        assert first["contracts_inserted"] == 14
        assert first["straddles_inserted"] == 7
        db.save_reference_lock(
            trading_date="2026-07-27",lock_time="09:21",
            reference_type="BATTLE_0921",index_symbol="NSE:NIFTY50-INDEX",
            expiry_date="2026-07-28",atm_strike=25000,spot_price=25010,
            atm_ce_close=130,atm_pe_close=120,payload={}
        )
        second = record_one_minute_snapshot(
            db,snapshot(25100,25115,120,105),
            index_symbol="NSE:NIFTY50-INDEX",
            timestamp="2026-07-27T09:22:00+05:30"
        )
        assert second["intelligence"]["rotation_count"] == 1
        stats = db.database_stats()
        assert stats["option_minute_bars"] == 28
        assert stats["strike_straddle_minute_bars"] == 14

print("ALL PREMIUM INTELLIGENCE V2 TESTS PASSED")
