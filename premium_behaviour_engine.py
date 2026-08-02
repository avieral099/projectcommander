from __future__ import annotations
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = "premium_intelligence_1m.db"

def sf(v, d=0.0):
    try: return float(v)
    except (TypeError, ValueError): return d

def si(v, d=0):
    try: return int(float(v))
    except (TypeError, ValueError): return d

def clamp(v): return max(0.0, min(float(v), 100.0))

@dataclass(frozen=True)
class PremiumBehaviourReport:
    index_symbol: str
    expiry_date: str
    timestamp: str
    theta_state: str
    theta_score: float
    gamma_state: str
    gamma_score: float
    rotation_state: str
    rotation_score: float
    rotation_count: int
    net_shift_points: int
    migration_state: str
    migration_score: float
    migration_target_strike: int
    time_pass_state: str
    time_pass_index: float
    regime: str
    commander_view: str
    reasons: List[str]
    warnings: List[str]
    metrics: Dict[str, Any]
    def to_dict(self): return asdict(self)

class PremiumBehaviourEngineV3:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        self.con = sqlite3.connect(self.db_path)
        self.con.row_factory = sqlite3.Row
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): self.close()
    def close(self): self.con.close()

    def latest(self, symbol, expiry=None):
        if expiry:
            row = self.con.execute(
                "SELECT * FROM intelligence_summaries WHERE index_symbol=? AND expiry_date=? ORDER BY timestamp DESC LIMIT 1",
                (symbol, expiry)
            ).fetchone()
        else:
            row = self.con.execute(
                "SELECT * FROM intelligence_summaries WHERE index_symbol=? ORDER BY timestamp DESC LIMIT 1",
                (symbol,)
            ).fetchone()
        if not row:
            raise RuntimeError(f"No premium intelligence data for {symbol}")
        return dict(row)

    def recent(self, symbol, expiry, limit=15):
        rows = self.con.execute(
            "SELECT * FROM intelligence_summaries WHERE index_symbol=? AND expiry_date=? ORDER BY timestamp DESC LIMIT ?",
            (symbol, expiry, limit)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def ladder(self, symbol, expiry, timestamp):
        rows = self.con.execute(
            "SELECT * FROM strike_straddle_minute_bars WHERE index_symbol=? AND expiry_date=? AND timestamp=? ORDER BY strike",
            (symbol, expiry, timestamp)
        ).fetchall()
        return [dict(r) for r in rows]

    def rotations(self, symbol, expiry, trading_date):
        row = self.con.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(shift_points),0) s FROM strike_rotations WHERE index_symbol=? AND expiry_date=? AND trading_date=?",
            (symbol, expiry, trading_date)
        ).fetchone()
        return si(row["c"]), si(row["s"])

    def analyse(self, index_symbol: str, expiry_date: Optional[str]=None, lookback_minutes: int=15):
        latest = self.latest(index_symbol, expiry_date)
        expiry = str(latest["expiry_date"])
        ts = str(latest["timestamp"])
        trading_date = str(latest["trading_date"])
        recent = self.recent(index_symbol, expiry, max(3, lookback_minutes))
        ladder = self.ladder(index_symbol, expiry, ts)
        rc, shift = self.rotations(index_symbol, expiry, trading_date)

        # Theta
        from_open = sf(latest.get("change_from_open_pct"))
        vs21 = sf(latest.get("change_vs_0921_pct"))
        vs25 = sf(latest.get("change_vs_0925_pct"))
        one = sf(latest.get("change_1m_pct"))
        refs = [x for x in (from_open, vs21, vs25) if x != 0]
        ref_decay = min(refs) if refs else from_open
        recent_changes = [sf(x.get("change_1m_pct")) for x in recent]
        persistence = (sum(1 for x in recent_changes if x < 0) / len(recent_changes) * 100) if recent_changes else 0
        theta_score = clamp(abs(min(ref_decay,0))*3 + persistence*.45 + abs(min(one,0))*5)
        theta_state = "HIGH" if theta_score>=75 else "MODERATE" if theta_score>=45 else "LOW" if theta_score>=20 else "ABSENT"

        # Gamma + migration
        strs = [sf(x.get("atm_straddle")) for x in recent if sf(x.get("atm_straddle"))>0]
        accel = 0.0
        if len(strs) >= 3:
            accel = (strs[-1]-strs[-2]) - (strs[-2]-strs[-3])

        leader = None
        if ladder:
            leader = max(ladder, key=lambda r: (sf(r.get("change_1m_pct")), sf(r.get("combined_volume"))))
        leader_step = si(leader.get("relative_steps")) if leader else 0
        leader_strike = si(leader.get("strike")) if leader else 0
        leader_change = sf(leader.get("change_1m_pct")) if leader else 0.0

        gamma_score = clamp(max(one,0)*12 + max(accel,0)*3 + max(leader_change,0)*8 + min(rc*10,30) + min(abs(shift)/10,20))
        gamma_state = "EXPLOSIVE" if gamma_score>=75 else "HIGH" if gamma_score>=50 else "BUILDING" if gamma_score>=25 else "LOW"

        rotation_score = clamp(rc*20 + abs(shift)/5)
        rotation_state = "NONE" if rc==0 else ("AGGRESSIVE_UP" if rotation_score>=75 and shift>0 else "AGGRESSIVE_DOWN" if rotation_score>=75 else "MODERATE_UP" if shift>0 else "MODERATE_DOWN")

        zero_movement = (
            abs(one) < 0.0001
            and abs(from_open) < 0.0001
            and abs(vs21) < 0.0001
            and abs(vs25) < 0.0001
            and rc == 0
            and all(
                abs(change) < 0.0001
                for change in recent_changes
            )
        )

        if zero_movement:
            migration_state = "ATM_CENTRED"
            migration_score = 0.0
            leader_strike = si(
                latest.get("atm_strike")
            )
            leader_change = 0.0
        else:
            migration_state = (
                "RIGHT_AGGRESSIVE"
                if leader_step >= 2
                else "RIGHT"
                if leader_step == 1
                else "LEFT_AGGRESSIVE"
                if leader_step <= -2
                else "LEFT"
                if leader_step == -1
                else "ATM_CENTRED"
            )
            migration_score = clamp(
                abs(leader_step) * 20
                + max(leader_change, 0) * 10
            )

        # Time pass
        tpi = 100 - min(abs(from_open)*4,35) - min(abs(one)*12,30) - min(rotation_score*.35,25) - min(gamma_score*.25,25)
        if theta_state in {"HIGH","MODERATE"}: tpi += 10
        tpi = clamp(tpi)
        tps = "HIGH" if tpi>=75 else "MODERATE" if tpi>=50 else "LOW" if tpi>=25 else "ABSENT"

        if gamma_state in {"EXPLOSIVE","HIGH"} and rc>0:
            regime, view = "ROTATIONAL_GAMMA_DAY", "DO NOT SHORT NAKED STRADDLE; WAIT FOR ROTATION STABILITY"
        elif gamma_state in {"EXPLOSIVE","HIGH"}:
            regime, view = "GAMMA_EXPANSION_DAY", "PREMIUM IS RUNNING; BUYING SETUPS HAVE PRIORITY"
        elif theta_state=="HIGH" and tps=="HIGH" and rc==0:
            regime, view = "PURE_THETA_DAY", "DO NOT CHASE OPTIONS; SHORT-PREMIUM EDGE BUILDING"
        elif theta_state in {"HIGH","MODERATE"} and rc>0:
            regime, view = "ROTATIONAL_THETA_DAY", "WAIT FOR ATM ROTATION TO SETTLE"
        elif migration_state != "ATM_CENTRED":
            regime, view = "PREMIUM_MIGRATION_DAY", "TRACK THE LEADING STRIKE; CURRENT ATM MAY BE LOSING CONTROL"
        elif tps=="HIGH":
            regime, view = "PREMIUM_FROZEN", "HOLD FIRE; MARKET HAS NOT EARNED CAPITAL"
        else:
            regime, view = "MIXED_PREMIUM_REGIME", "NO CLEAN EDGE; REQUIRE MORE DATA"

        reasons = [
            f"Theta {theta_state} ({theta_score:.2f})",
            f"Gamma {gamma_state} ({gamma_score:.2f})",
            f"Rotation {rotation_state} ({rc} shifts)",
            f"Migration {migration_state} toward {leader_strike}",
            f"Time-pass index {tpi:.2f}",
        ]
        warnings = []
        if rc>0: warnings.append("ATM strike is rotating")
        if gamma_state in {"EXPLOSIVE","HIGH"}: warnings.append("Premium expansion risk elevated")
        if migration_state!="ATM_CENTRED": warnings.append("Premium leadership moved away from ATM")

        return PremiumBehaviourReport(
            index_symbol, expiry, ts,
            theta_state, round(theta_score,2),
            gamma_state, round(gamma_score,2),
            rotation_state, round(rotation_score,2), rc, shift,
            migration_state, round(migration_score,2), leader_strike,
            tps, round(tpi,2), regime, view,
            reasons, warnings,
            {
                "atm_straddle": sf(latest.get("atm_straddle")),
                "premium_remaining_pct": sf(latest.get("premium_remaining_pct")),
                "change_from_open_pct": from_open,
                "change_vs_0921_pct": vs21,
                "change_vs_0925_pct": vs25,
                "gamma_acceleration": round(accel,2),
                "migration_distance_from_atm": leader_strike-si(latest.get("atm_strike")),
            }
        )

def print_premium_behaviour(report: PremiumBehaviourReport, width: int=92):
    print("\n"+"="*width)
    print("PREMIUM BEHAVIOUR INTELLIGENCE V3".center(width))
    print("="*width)
    print(f"THETA DECAY               : {report.theta_state} [{report.theta_score:.2f}]")
    print(f"GAMMA PRESSURE            : {report.gamma_state} [{report.gamma_score:.2f}]")
    print(f"STRIKE ROTATION           : {report.rotation_state} [{report.rotation_score:.2f}]")
    print(f"PREMIUM MIGRATION         : {report.migration_state} -> {report.migration_target_strike}")
    print(f"TIME PASS INDEX           : {report.time_pass_index:.2f}% [{report.time_pass_state}]")
    print("-"*width)
    print(f"CURRENT REGIME            : {report.regime}")
    print(f"COMMANDER VIEW            : {report.commander_view}")
    print("="*width)
