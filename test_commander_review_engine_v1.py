from pathlib import Path
import sqlite3
import tempfile

from commander_review_engine import generate_report

SCHEMA = """
CREATE TABLE intelligence_summaries (
timestamp TEXT NOT NULL,trading_date TEXT NOT NULL,index_symbol TEXT NOT NULL,
expiry_date TEXT NOT NULL,spot_price REAL NOT NULL,atm_strike INTEGER NOT NULL,
atm_straddle REAL NOT NULL,change_1m_pct REAL NOT NULL,change_from_open_pct REAL NOT NULL,
overnight_change_pct REAL NOT NULL,change_vs_0921_pct REAL NOT NULL,
change_vs_0925_pct REAL NOT NULL,premium_remaining_pct REAL NOT NULL,
rotation_count INTEGER NOT NULL,net_shift_points INTEGER NOT NULL,
decay_state TEXT NOT NULL,rotation_state TEXT NOT NULL,commander_state TEXT NOT NULL,
pdc REAL NOT NULL DEFAULT 0,pdh REAL NOT NULL DEFAULT 0,pdl REAL NOT NULL DEFAULT 0,
vwap_state TEXT NOT NULL DEFAULT 'UNKNOWN',ema_structure TEXT NOT NULL DEFAULT 'UNKNOWN',
supertrend_state TEXT NOT NULL DEFAULT 'UNKNOWN',or_status TEXT NOT NULL DEFAULT 'UNKNOWN',
driver_state TEXT NOT NULL DEFAULT 'UNKNOWN',premium_flow_side TEXT NOT NULL DEFAULT 'BALANCED',
straddle_structure TEXT NOT NULL DEFAULT 'UNKNOWN',straddle_bias TEXT NOT NULL DEFAULT 'NEUTRAL',
battle_zone TEXT NOT NULL DEFAULT 'UNKNOWN',battle_status TEXT NOT NULL DEFAULT 'UNKNOWN',
battle_score REAL NOT NULL DEFAULT 0,evidence_verdict TEXT NOT NULL DEFAULT 'NO_BIAS',
evidence_score REAL NOT NULL DEFAULT 0,call_confidence REAL NOT NULL DEFAULT 0,
put_confidence REAL NOT NULL DEFAULT 0,engine_agreement INTEGER NOT NULL DEFAULT 0,
PRIMARY KEY(timestamp,index_symbol,expiry_date));
"""

def add(conn, ts, spot, verdict):
    conn.execute("""
    INSERT INTO intelligence_summaries (
    timestamp,trading_date,index_symbol,expiry_date,spot_price,atm_strike,atm_straddle,
    change_1m_pct,change_from_open_pct,overnight_change_pct,change_vs_0921_pct,
    change_vs_0925_pct,premium_remaining_pct,rotation_count,net_shift_points,
    decay_state,rotation_state,commander_state,premium_flow_side,straddle_structure,
    straddle_bias,battle_zone,battle_status,battle_score,evidence_verdict,evidence_score,
    call_confidence,put_confidence,engine_agreement)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (ts,"2026-07-28","NSE:NIFTY50-INDEX","2026-07-28",spot,24000,100,
          0,0,0,0,0,100,0,0,"SLOW_DECAY","NO_ROTATION","MIXED_PREMIUM_REGIME",
          "BALANCED","DECAY_BREAKDOWN","SHORT_STRADDLE","NEUTRAL","WAIT",4,
          verdict,70,70 if "CALL" in verdict else 0,70 if "PUT" in verdict else 0,4))

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    db = tmp / "test.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(SCHEMA)
        add(conn,"2026-07-28T09:15:00+05:30",24000,"CALL_BIAS")
        add(conn,"2026-07-28T09:30:00+05:30",24030,"PUT_BIAS")
        add(conn,"2026-07-28T09:45:00+05:30",24000,"NO_BIAS")
        conn.commit()
    txt, csv = generate_report(db,"2026-07-28",15,tmp)
    assert txt.exists() and csv.exists()
    assert "AUTOMATIC DECISION AUDIT" in txt.read_text()
    print("ALL COMMANDER REVIEW ENGINE V1 TESTS PASSED")
