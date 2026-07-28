import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from premium_behaviour_engine import PremiumBehaviourEngineV3

with TemporaryDirectory() as tmp:
    db = Path(tmp)/"test.db"
    con = sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE intelligence_summaries (
      timestamp TEXT,trading_date TEXT,index_symbol TEXT,expiry_date TEXT,
      spot_price REAL,atm_strike INTEGER,atm_straddle REAL,change_1m_pct REAL,
      change_from_open_pct REAL,overnight_change_pct REAL,change_vs_0921_pct REAL,
      change_vs_0925_pct REAL,premium_remaining_pct REAL,rotation_count INTEGER,
      net_shift_points INTEGER,decay_state TEXT,rotation_state TEXT,commander_state TEXT
    );
    CREATE TABLE strike_straddle_minute_bars (
      timestamp TEXT,trading_date TEXT,index_symbol TEXT,index_name TEXT,expiry_date TEXT,
      spot_price REAL,atm_strike INTEGER,strike INTEGER,relative_steps INTEGER,
      ce_symbol TEXT,pe_symbol TEXT,ce_ltp REAL,pe_ltp REAL,straddle REAL,
      session_open REAL,previous_close REAL,change_1m REAL,change_1m_pct REAL,
      change_from_open REAL,change_from_open_pct REAL,overnight_change REAL,
      overnight_change_pct REAL,combined_oi INTEGER,combined_volume INTEGER
    );
    CREATE TABLE strike_rotations (
      timestamp TEXT,trading_date TEXT,index_symbol TEXT,expiry_date TEXT,
      old_atm INTEGER,new_atm INTEGER,shift_points INTEGER,direction TEXT
    );
    """)
    for i in range(5):
        con.execute("INSERT INTO intelligence_summaries VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(
          f"2026-07-27T09:{21+i:02d}:00+05:30","2026-07-27","NSE:NIFTY50-INDEX","2026-07-28",
          25000+i*20,25100 if i>=2 else 25000,250-i*4,-1.5,-i*2,-4,-i*2,0,100-i*2,
          1 if i>=2 else 0,100 if i>=2 else 0,"SLOW_DECAY","UPWARD_ROTATION","MIXED"
        ))
    ts="2026-07-27T09:25:00+05:30"
    for rel,strike,ch,vol in [(-3,24800,-2,1000),(-2,24900,-1,1100),(-1,25000,.5,1200),(0,25100,1,1500),(1,25200,4.5,2200),(2,25300,7,2600),(3,25400,9,3000)]:
        con.execute("INSERT INTO strike_straddle_minute_bars VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(
          ts,"2026-07-27","NSE:NIFTY50-INDEX","NIFTY","2026-07-28",25080,25100,strike,rel,
          "CE","PE",100,100,200,220,240,ch*2,ch,-20,-9,-20,-8,10000,vol
        ))
    con.execute("INSERT INTO strike_rotations VALUES (?,?,?,?,?,?,?,?)",(
      ts,"2026-07-27","NSE:NIFTY50-INDEX","2026-07-28",25000,25100,100,"UP"
    ))
    con.commit(); con.close()

    with PremiumBehaviourEngineV3(db) as engine:
        report=engine.analyse("NSE:NIFTY50-INDEX","2026-07-28")
        assert report.rotation_count==1
        assert report.migration_state=="RIGHT_AGGRESSIVE"
        assert report.migration_target_strike==25400

print("ALL PREMIUM BEHAVIOUR V3 TESTS PASSED")
