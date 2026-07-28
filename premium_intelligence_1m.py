from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_DB_PATH = "premium_intelligence_1m.db"

LADDER_LABELS = (
    "ITM3_CE", "ITM2_CE", "ITM1_CE", "ATM_CE", "OTM1_CE", "OTM2_CE", "OTM3_CE",
    "ITM3_PE", "ITM2_PE", "ITM1_PE", "ATM_PE", "OTM1_PE", "OTM2_PE", "OTM3_PE",
)

INTELLIGENCE_CONTEXT_COLUMNS = {
    "pdc": "REAL NOT NULL DEFAULT 0",
    "pdh": "REAL NOT NULL DEFAULT 0",
    "pdl": "REAL NOT NULL DEFAULT 0",
    "vwap_state": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
    "ema_structure": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
    "supertrend_state": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
    "or_status": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
    "driver_state": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
    "premium_flow_side": "TEXT NOT NULL DEFAULT 'BALANCED'",
    "straddle_structure": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
    "straddle_bias": "TEXT NOT NULL DEFAULT 'NEUTRAL'",
    "battle_zone": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
    "battle_status": "TEXT NOT NULL DEFAULT 'UNKNOWN'",
    "battle_score": "REAL NOT NULL DEFAULT 0",
    "evidence_verdict": "TEXT NOT NULL DEFAULT 'NO_BIAS'",
    "evidence_score": "REAL NOT NULL DEFAULT 0",
    "call_confidence": "REAL NOT NULL DEFAULT 0",
    "put_confidence": "REAL NOT NULL DEFAULT 0",
    "engine_agreement": "INTEGER NOT NULL DEFAULT 0",
}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def pct_change(current: float, reference: float) -> float:
    return ((current - reference) / reference) * 100 if reference > 0 else 0.0


def normalise_timestamp(value: Optional[str]) -> str:
    if value:
        dt = datetime.fromisoformat(value)
        dt = dt.replace(tzinfo=IST) if dt.tzinfo is None else dt.astimezone(IST)
    else:
        dt = datetime.now(IST)
    return dt.replace(second=0, microsecond=0).isoformat()


def classify_decay(
    change_1m: float,
    from_open: float,
    vs_0921: float,
    vs_0925: float,
) -> str:
    reference = vs_0925 if vs_0925 else vs_0921

    if change_1m >= 3 or reference >= 5:
        return "PREMIUM_EXPANSION"
    if reference <= -15 or from_open <= -25:
        return "FAST_DECAY"
    if reference <= -5 or from_open <= -10:
        return "SLOW_DECAY"
    if abs(change_1m) <= 1 and abs(from_open) <= 5:
        return "TIME_PASS"
    return "BALANCED"


class PremiumIntelligence1M:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()
        self._migrate_schema()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self):
        self.connection.close()

    def _create_schema(self):
        self.connection.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;

        CREATE TABLE IF NOT EXISTS option_minute_bars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            trading_date TEXT NOT NULL,
            index_symbol TEXT NOT NULL,
            index_name TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            spot_price REAL NOT NULL,
            atm_strike INTEGER NOT NULL,
            ladder_label TEXT NOT NULL,
            option_symbol TEXT NOT NULL,
            strike INTEGER NOT NULL,
            option_type TEXT NOT NULL,
            ltp REAL NOT NULL,
            change_value REAL NOT NULL,
            change_pct REAL NOT NULL,
            previous_close REAL NOT NULL,
            bid REAL NOT NULL,
            ask REAL NOT NULL,
            spread REAL NOT NULL,
            volume INTEGER NOT NULL,
            oi INTEGER NOT NULL,
            iv REAL NOT NULL,
            delta REAL NOT NULL,
            gamma REAL NOT NULL,
            theta REAL NOT NULL,
            vega REAL NOT NULL,
            UNIQUE(timestamp, option_symbol)
        );

        CREATE TABLE IF NOT EXISTS strike_straddle_minute_bars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            trading_date TEXT NOT NULL,
            index_symbol TEXT NOT NULL,
            index_name TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            spot_price REAL NOT NULL,
            atm_strike INTEGER NOT NULL,
            strike INTEGER NOT NULL,
            relative_steps INTEGER NOT NULL,
            ce_symbol TEXT NOT NULL,
            pe_symbol TEXT NOT NULL,
            ce_ltp REAL NOT NULL,
            pe_ltp REAL NOT NULL,
            straddle REAL NOT NULL,
            session_open REAL NOT NULL,
            previous_close REAL NOT NULL,
            change_1m REAL NOT NULL,
            change_1m_pct REAL NOT NULL,
            change_from_open REAL NOT NULL,
            change_from_open_pct REAL NOT NULL,
            overnight_change REAL NOT NULL,
            overnight_change_pct REAL NOT NULL,
            combined_oi INTEGER NOT NULL,
            combined_volume INTEGER NOT NULL,
            UNIQUE(timestamp, index_symbol, expiry_date, strike)
        );

        CREATE TABLE IF NOT EXISTS session_anchors (
            trading_date TEXT NOT NULL,
            index_symbol TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            strike INTEGER NOT NULL,
            first_timestamp TEXT NOT NULL,
            open_straddle REAL NOT NULL,
            PRIMARY KEY(trading_date, index_symbol, expiry_date, strike)
        );

        CREATE TABLE IF NOT EXISTS strike_rotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            trading_date TEXT NOT NULL,
            index_symbol TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            old_atm INTEGER NOT NULL,
            new_atm INTEGER NOT NULL,
            shift_points INTEGER NOT NULL,
            direction TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reference_locks (
            trading_date TEXT NOT NULL,
            reference_type TEXT NOT NULL,
            lock_time TEXT NOT NULL,
            index_symbol TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            atm_strike INTEGER NOT NULL,
            spot_price REAL NOT NULL,
            atm_ce REAL NOT NULL,
            atm_pe REAL NOT NULL,
            straddle REAL NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY(trading_date, reference_type, index_symbol, expiry_date)
        );

        CREATE TABLE IF NOT EXISTS intelligence_summaries (
            timestamp TEXT NOT NULL,
            trading_date TEXT NOT NULL,
            index_symbol TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            spot_price REAL NOT NULL,
            atm_strike INTEGER NOT NULL,
            atm_straddle REAL NOT NULL,
            change_1m_pct REAL NOT NULL,
            change_from_open_pct REAL NOT NULL,
            overnight_change_pct REAL NOT NULL,
            change_vs_0921_pct REAL NOT NULL,
            change_vs_0925_pct REAL NOT NULL,
            premium_remaining_pct REAL NOT NULL,
            rotation_count INTEGER NOT NULL,
            net_shift_points INTEGER NOT NULL,
            decay_state TEXT NOT NULL,
            rotation_state TEXT NOT NULL,
            commander_state TEXT NOT NULL,
            PRIMARY KEY(timestamp, index_symbol, expiry_date)
        );
        """)
        self.connection.commit()

    def _migrate_schema(self):
        existing = {
            row["name"]
            for row in self.connection.execute(
                "PRAGMA table_info(intelligence_summaries)"
            ).fetchall()
        }

        for column, definition in INTELLIGENCE_CONTEXT_COLUMNS.items():
            if column not in existing:
                self.connection.execute(
                    f"ALTER TABLE intelligence_summaries "
                    f"ADD COLUMN {column} {definition}"
                )

        self.connection.commit()

    def save_reference_lock(
        self,
        *,
        trading_date,
        lock_time,
        reference_type,
        index_symbol,
        expiry_date,
        atm_strike,
        spot_price,
        atm_ce_close,
        atm_pe_close,
        payload,
    ):
        self.connection.execute("""
        INSERT OR REPLACE INTO reference_locks (
            trading_date, reference_type, lock_time, index_symbol,
            expiry_date, atm_strike, spot_price, atm_ce, atm_pe,
            straddle, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trading_date,
            reference_type,
            lock_time,
            index_symbol,
            expiry_date,
            atm_strike,
            spot_price,
            atm_ce_close,
            atm_pe_close,
            atm_ce_close + atm_pe_close,
            json.dumps(dict(payload), default=str),
        ))
        self.connection.commit()

    def reference(self, trading_date, reference_type, index_symbol, expiry_date):
        row = self.connection.execute("""
        SELECT *
        FROM reference_locks
        WHERE trading_date=?
          AND reference_type=?
          AND index_symbol=?
          AND expiry_date=?
        """, (
            trading_date,
            reference_type,
            index_symbol,
            expiry_date,
        )).fetchone()
        return dict(row) if row else None

    def session_open(
        self,
        trading_date,
        index_symbol,
        expiry_date,
        strike,
        timestamp,
        current,
    ):
        row = self.connection.execute("""
        SELECT open_straddle
        FROM session_anchors
        WHERE trading_date=?
          AND index_symbol=?
          AND expiry_date=?
          AND strike=?
        """, (
            trading_date,
            index_symbol,
            expiry_date,
            strike,
        )).fetchone()

        if row:
            return safe_float(row["open_straddle"])

        self.connection.execute("""
        INSERT INTO session_anchors
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            trading_date,
            index_symbol,
            expiry_date,
            strike,
            timestamp,
            current,
        ))
        self.connection.commit()
        return current

    def latest_straddle(self, index_symbol, expiry_date, strike):
        row = self.connection.execute("""
        SELECT *
        FROM strike_straddle_minute_bars
        WHERE index_symbol=?
          AND expiry_date=?
          AND strike=?
        ORDER BY timestamp DESC
        LIMIT 1
        """, (
            index_symbol,
            expiry_date,
            strike,
        )).fetchone()
        return dict(row) if row else None

    def latest_summary(self, index_symbol, expiry_date):
        row = self.connection.execute("""
        SELECT *
        FROM intelligence_summaries
        WHERE index_symbol=?
          AND expiry_date=?
        ORDER BY timestamp DESC
        LIMIT 1
        """, (
            index_symbol,
            expiry_date,
        )).fetchone()
        return dict(row) if row else None

    def rotation_summary(self, trading_date, index_symbol, expiry_date):
        row = self.connection.execute("""
        SELECT
            COUNT(*) AS count,
            COALESCE(SUM(shift_points), 0) AS shift
        FROM strike_rotations
        WHERE trading_date=?
          AND index_symbol=?
          AND expiry_date=?
        """, (
            trading_date,
            index_symbol,
            expiry_date,
        )).fetchone()
        return safe_int(row["count"]), safe_int(row["shift"])

    def enrich_intelligence_summary(
        self,
        *,
        timestamp: str,
        index_symbol: str,
        expiry_date: str,
        context: Mapping[str, Any],
    ) -> bool:
        allowed = set(INTELLIGENCE_CONTEXT_COLUMNS)
        values = {
            key: context[key]
            for key in context
            if key in allowed
        }

        if not values:
            return False

        assignments = ", ".join(
            f"{column}=?" for column in values
        )

        cursor = self.connection.execute(
            f"""
            UPDATE intelligence_summaries
            SET {assignments}
            WHERE timestamp=?
              AND index_symbol=?
              AND expiry_date=?
            """,
            (
                *values.values(),
                timestamp,
                index_symbol,
                expiry_date,
            ),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def database_stats(self):
        tables = (
            "option_minute_bars",
            "strike_straddle_minute_bars",
            "session_anchors",
            "strike_rotations",
            "reference_locks",
            "intelligence_summaries",
        )
        return {
            table: safe_int(
                self.connection.execute(
                    f"SELECT COUNT(*) AS c FROM {table}"
                ).fetchone()["c"]
            )
            for table in tables
        }


def _contract_ltp(contracts: Mapping[str, Any], label: str) -> float:
    contract = contracts.get(label) or {}
    return safe_float(contract.get("ltp"))


def _save_due_reference_locks(
    database: PremiumIntelligence1M,
    *,
    timestamp: str,
    trading_date: str,
    index_symbol: str,
    expiry: str,
    atm: int,
    spot: float,
    contracts: Mapping[str, Any],
    snapshot: Mapping[str, Any],
):
    minute = datetime.fromisoformat(timestamp).astimezone(IST).strftime("%H:%M")
    atm_ce = _contract_ltp(contracts, "ATM_CE")
    atm_pe = _contract_ltp(contracts, "ATM_PE")

    if atm_ce <= 0 or atm_pe <= 0:
        return []

    saved = []

    due_locks = {
        "09:21": "BATTLE_0921",
        "09:25": "STRADDLE_0925",
    }

    reference_type = due_locks.get(minute)
    if not reference_type:
        return saved

    existing = database.reference(
        trading_date,
        reference_type,
        index_symbol,
        expiry,
    )

    if existing:
        return saved

    database.save_reference_lock(
        trading_date=trading_date,
        lock_time=minute,
        reference_type=reference_type,
        index_symbol=index_symbol,
        expiry_date=expiry,
        atm_strike=atm,
        spot_price=spot,
        atm_ce_close=atm_ce,
        atm_pe_close=atm_pe,
        payload=snapshot,
    )
    saved.append(reference_type)
    return saved


def record_one_minute_snapshot(
    database: PremiumIntelligence1M,
    snapshot: Mapping[str, Any],
    *,
    index_symbol: str,
    timestamp: Optional[str] = None,
    reference_type: str = "LIVE",
):
    del reference_type

    timestamp = normalise_timestamp(timestamp)
    trading_date = timestamp[:10]
    index_name = str(snapshot.get("index_name") or index_symbol)
    expiry = str(snapshot.get("expiry_date") or "UNKNOWN")
    spot = safe_float(snapshot.get("spot_price"))
    atm = safe_int(snapshot.get("atm_strike"))
    step = max(safe_int(snapshot.get("strike_step")), 1)
    contracts = snapshot.get("contracts") or {}

    previous_summary = database.latest_summary(index_symbol, expiry)
    previous_atm = (
        safe_int(previous_summary.get("atm_strike"))
        if previous_summary
        else atm
    )

    bars = []
    missing = []

    for label in LADDER_LABELS:
        contract = contracts.get(label)
        if not contract:
            missing.append(label)
            continue

        ltp = safe_float(contract.get("ltp"))
        change = safe_float(contract.get("change"))
        previous_close = ltp - change
        bid = safe_float(contract.get("bid"))
        ask = safe_float(contract.get("ask"))

        bars.append((
            timestamp,
            trading_date,
            index_symbol,
            index_name,
            expiry,
            spot,
            atm,
            label,
            str(contract.get("symbol") or f"{index_symbol}:{label}"),
            safe_int(contract.get("strike")),
            str(contract.get("option_type") or "").upper(),
            ltp,
            change,
            safe_float(contract.get("change_pct")),
            previous_close if previous_close > 0 else ltp,
            bid,
            ask,
            max(ask - bid, 0.0),
            safe_int(contract.get("volume")),
            safe_int(contract.get("oi")),
            safe_float(contract.get("iv")),
            safe_float(contract.get("delta")),
            safe_float(contract.get("gamma")),
            safe_float(contract.get("theta")),
            safe_float(contract.get("vega")),
        ))

    database.connection.executemany("""
    INSERT OR REPLACE INTO option_minute_bars (
        timestamp, trading_date, index_symbol, index_name, expiry_date,
        spot_price, atm_strike, ladder_label, option_symbol, strike,
        option_type, ltp, change_value, change_pct, previous_close,
        bid, ask, spread, volume, oi, iv, delta, gamma, theta, vega
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?
    )
    """, bars)
    database.connection.commit()

    if previous_summary and previous_atm != atm:
        shift = atm - previous_atm
        database.connection.execute("""
        INSERT INTO strike_rotations (
            timestamp, trading_date, index_symbol, expiry_date,
            old_atm, new_atm, shift_points, direction
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            trading_date,
            index_symbol,
            expiry,
            previous_atm,
            atm,
            shift,
            "UP" if shift > 0 else "DOWN",
        ))
        database.connection.commit()

    reference_locks_saved = _save_due_reference_locks(
        database,
        timestamp=timestamp,
        trading_date=trading_date,
        index_symbol=index_symbol,
        expiry=expiry,
        atm=atm,
        spot=spot,
        contracts=contracts,
        snapshot=snapshot,
    )

    pairs = {}
    for row in bars:
        strike = row[9]
        option_type = row[10]
        pairs.setdefault(strike, {})[option_type] = row

    inserted_straddles = 0
    atm_data = None

    for strike, pair in sorted(pairs.items()):
        if "CE" not in pair or "PE" not in pair:
            continue

        ce, pe = pair["CE"], pair["PE"]
        ce_ltp, pe_ltp = ce[11], pe[11]
        current = ce_ltp + pe_ltp
        previous_close = ce[14] + pe[14]

        session_open = database.session_open(
            trading_date,
            index_symbol,
            expiry,
            strike,
            timestamp,
            current,
        )

        latest = database.latest_straddle(
            index_symbol,
            expiry,
            strike,
        )
        previous_minute = (
            safe_float(latest.get("straddle"))
            if latest
            else current
        )

        relative_steps = int((strike - atm) / step)
        change_1m = current - previous_minute
        from_open = current - session_open
        overnight = session_open - previous_close

        database.connection.execute("""
        INSERT OR REPLACE INTO strike_straddle_minute_bars (
            timestamp, trading_date, index_symbol, index_name, expiry_date,
            spot_price, atm_strike, strike, relative_steps, ce_symbol,
            pe_symbol, ce_ltp, pe_ltp, straddle, session_open,
            previous_close, change_1m, change_1m_pct, change_from_open,
            change_from_open_pct, overnight_change, overnight_change_pct,
            combined_oi, combined_volume
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?
        )
        """, (
            timestamp,
            trading_date,
            index_symbol,
            index_name,
            expiry,
            spot,
            atm,
            strike,
            relative_steps,
            ce[8],
            pe[8],
            ce_ltp,
            pe_ltp,
            current,
            session_open,
            previous_close,
            change_1m,
            pct_change(current, previous_minute),
            from_open,
            pct_change(current, session_open),
            overnight,
            pct_change(session_open, previous_close),
            ce[19] + pe[19],
            ce[18] + pe[18],
        ))
        database.connection.commit()
        inserted_straddles += 1

        if strike == atm:
            atm_data = {
                "straddle": current,
                "change_1m_pct": pct_change(current, previous_minute),
                "change_from_open_pct": pct_change(current, session_open),
                "overnight_change_pct": pct_change(
                    session_open,
                    previous_close,
                ),
                "session_open": session_open,
            }

    intelligence = None

    if atm_data:
        ref21 = database.reference(
            trading_date,
            "BATTLE_0921",
            index_symbol,
            expiry,
        )
        ref25 = database.reference(
            trading_date,
            "STRADDLE_0925",
            index_symbol,
            expiry,
        )

        ref21_value = safe_float(ref21.get("straddle")) if ref21 else 0.0
        ref25_value = safe_float(ref25.get("straddle")) if ref25 else 0.0

        vs21 = (
            pct_change(atm_data["straddle"], ref21_value)
            if ref21_value
            else 0.0
        )
        vs25 = (
            pct_change(atm_data["straddle"], ref25_value)
            if ref25_value
            else 0.0
        )

        rotation_count, net_shift = database.rotation_summary(
            trading_date,
            index_symbol,
            expiry,
        )

        rotation_state = (
            "NO_ROTATION"
            if rotation_count == 0
            else "AGGRESSIVE_UPWARD_ROTATION"
            if rotation_count >= 3 and net_shift > 0
            else "AGGRESSIVE_DOWNWARD_ROTATION"
            if rotation_count >= 3 and net_shift < 0
            else "UPWARD_ROTATION"
            if net_shift > 0
            else "DOWNWARD_ROTATION"
        )

        decay_state = classify_decay(
            atm_data["change_1m_pct"],
            atm_data["change_from_open_pct"],
            vs21,
            vs25,
        )

        commander_state = (
            "ROTATION_WITH_EXPANSION"
            if decay_state == "PREMIUM_EXPANSION" and rotation_count > 0
            else "THETA_DOMINANT"
            if decay_state in {"FAST_DECAY", "SLOW_DECAY"}
            and rotation_count == 0
            else "PREMIUM_FROZEN"
            if decay_state == "TIME_PASS" and rotation_count == 0
            else "MIXED_PREMIUM_REGIME"
        )

        remaining = (
            (atm_data["straddle"] / atm_data["session_open"]) * 100
            if atm_data["session_open"] > 0
            else 0.0
        )

        intelligence = {
            "timestamp": timestamp,
            "trading_date": trading_date,
            "index_symbol": index_symbol,
            "expiry_date": expiry,
            "spot_price": spot,
            "atm_strike": atm,
            "atm_straddle": round(atm_data["straddle"], 2),
            "change_1m_pct": round(atm_data["change_1m_pct"], 4),
            "change_from_open_pct": round(
                atm_data["change_from_open_pct"],
                4,
            ),
            "overnight_change_pct": round(
                atm_data["overnight_change_pct"],
                4,
            ),
            "change_vs_0921_pct": round(vs21, 4),
            "change_vs_0925_pct": round(vs25, 4),
            "premium_remaining_pct": round(remaining, 2),
            "rotation_count": rotation_count,
            "net_shift_points": net_shift,
            "decay_state": decay_state,
            "rotation_state": rotation_state,
            "commander_state": commander_state,
        }

        database.connection.execute("""
        INSERT OR REPLACE INTO intelligence_summaries (
            timestamp, trading_date, index_symbol, expiry_date,
            spot_price, atm_strike, atm_straddle, change_1m_pct,
            change_from_open_pct, overnight_change_pct,
            change_vs_0921_pct, change_vs_0925_pct,
            premium_remaining_pct, rotation_count, net_shift_points,
            decay_state, rotation_state, commander_state
        ) VALUES (
            :timestamp, :trading_date, :index_symbol, :expiry_date,
            :spot_price, :atm_strike, :atm_straddle, :change_1m_pct,
            :change_from_open_pct, :overnight_change_pct,
            :change_vs_0921_pct, :change_vs_0925_pct,
            :premium_remaining_pct, :rotation_count, :net_shift_points,
            :decay_state, :rotation_state, :commander_state
        )
        """, intelligence)
        database.connection.commit()

    return {
        "status": "RECORDED",
        "resolution": "1",
        "timestamp": timestamp,
        "contracts_inserted": len(bars),
        "straddles_inserted": inserted_straddles,
        "missing_labels": missing,
        "reference_locks_saved": reference_locks_saved,
        "intelligence": intelligence,
    }


def print_intelligence(result: Mapping[str, Any], width: int = 92):
    intel = result.get("intelligence") or {}

    print("\n" + "=" * width)
    print("PREMIUM INTELLIGENCE V3".center(width))
    print("=" * width)
    print(
        f"CONTRACTS RECORDED        : "
        f"{result.get('contracts_inserted', 0)}"
    )
    print(
        f"STRADDLES RECORDED        : "
        f"{result.get('straddles_inserted', 0)}"
    )

    locks = result.get("reference_locks_saved") or []
    if locks:
        print(
            f"REFERENCE LOCKS SAVED     : "
            f"{', '.join(locks)}"
        )

    if intel:
        print(
            f"ATM STRADDLE              : "
            f"₹{safe_float(intel.get('atm_straddle')):.2f}"
        )
        print(
            f"PREMIUM REMAINING         : "
            f"{safe_float(intel.get('premium_remaining_pct')):.2f}%"
        )
        print(
            f"DECAY STATE               : "
            f"{intel.get('decay_state')}"
        )
        print(
            f"ROTATION STATE            : "
            f"{intel.get('rotation_state')}"
        )
        print(
            f"COMMANDER STATE           : "
            f"{intel.get('commander_state')}"
        )

    print("=" * width)
