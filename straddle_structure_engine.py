"""
OPERATION COMMANDER
Module  : Straddle Structure Engine V1
Purpose : 09:21 ATM straddle ke price behaviour ko map karna.

This engine answers only:
    "Current straddle structure short-straddle seller ke liye kya hai?"

It never issues:
    BUY CALL
    BUY PUT

Outputs:
    LONG_STRADDLE
    SHORT_STRADDLE
    NEUTRAL

Structure inputs:
    09:21 reference
    15-minute opening-range high/low
    Straddle VWAP
    EMA75 high/low envelope
    Current straddle price
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")
DEFAULT_DB_PATH = "premium_intelligence_1m.db"

OPENING_RANGE_START = time(9, 15)
OPENING_RANGE_END = time(9, 30)
REFERENCE_TIME = time(9, 21)

EMA_PERIOD = 75
DECAY_CONFIRMATION_BARS = 2


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value))

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    else:
        parsed = parsed.astimezone(IST)

    return parsed


def ema(values: Sequence[float], period: int) -> float:
    clean = [
        safe_float(value)
        for value in values
        if safe_float(value) > 0
    ]

    if not clean:
        return 0.0

    multiplier = 2 / (period + 1)
    result = clean[0]

    for value in clean[1:]:
        result = (
            value * multiplier
            + result * (1 - multiplier)
        )

    return result


@dataclass(frozen=True)
class StraddleStructureReport:
    index_symbol: str
    expiry_date: str
    trading_date: str
    timestamp: str
    atm_strike: int

    reference_0921: float
    current_straddle: float
    change_vs_0921: float
    change_vs_0921_pct: float

    opening_range_ready: bool
    opening_range_high: float
    opening_range_low: float
    opening_range_width: float

    straddle_vwap: float
    ema75_high: float
    ema75_low: float

    above_orh: bool
    below_orl: bool
    above_vwap: bool
    below_vwap: bool
    above_ema75_high: bool
    below_ema75_low: bool
    inside_opening_range: bool
    inside_ema_envelope: bool

    structure_state: str
    straddle_bias: str
    short_straddle_stance: str
    theta_state: str
    gamma_state: str
    confidence: float

    data_quality: str
    reasons: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StraddleStructureEngine:
    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
    ) -> None:
        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Premium intelligence database not found: "
                f"{self.db_path}"
            )

        self.connection = sqlite3.connect(
            self.db_path
        )
        self.connection.row_factory = sqlite3.Row

        self._straddle_table = (
            self._resolve_straddle_table()
        )

    def __enter__(
        self,
    ) -> "StraddleStructureEngine":
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def _table_exists(
        self,
        table_name: str,
    ) -> bool:
        row = self.connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table_name,),
        ).fetchone()

        return row is not None

    def _columns(
        self,
        table_name: str,
    ) -> set[str]:
        rows = self.connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()

        return {
            str(row["name"])
            for row in rows
        }

    def _resolve_straddle_table(self) -> str:
        for table_name in (
            "strike_straddle_minute_bars",
            "straddle_minute_bars",
        ):
            if self._table_exists(table_name):
                return table_name

        raise RuntimeError(
            "No straddle-minute table found. "
            "Premium Intelligence V2 recorder is required."
        )

    def _latest_summary(
        self,
        index_symbol: str,
        expiry_date: Optional[str],
    ) -> Dict[str, Any]:
        if not self._table_exists(
            "intelligence_summaries"
        ):
            raise RuntimeError(
                "intelligence_summaries table not found"
            )

        if expiry_date:
            row = self.connection.execute(
                """
                SELECT *
                FROM intelligence_summaries
                WHERE index_symbol = ?
                  AND expiry_date = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (
                    index_symbol,
                    expiry_date,
                ),
            ).fetchone()
        else:
            row = self.connection.execute(
                """
                SELECT *
                FROM intelligence_summaries
                WHERE index_symbol = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (index_symbol,),
            ).fetchone()

        if not row:
            raise RuntimeError(
                f"No premium intelligence data for "
                f"{index_symbol}"
            )

        return dict(row)

    def _session_rows(
        self,
        index_symbol: str,
        expiry_date: str,
        trading_date: str,
        atm_strike: int,
    ) -> List[Dict[str, Any]]:
        columns = self._columns(
            self._straddle_table
        )

        strike_filter = (
            "AND strike = ?"
            if "strike" in columns
            else "AND atm_strike = ?"
        )

        query = f"""
            SELECT *
            FROM {self._straddle_table}
            WHERE index_symbol = ?
              AND expiry_date = ?
              AND trading_date = ?
              {strike_filter}
            ORDER BY timestamp
        """

        rows = self.connection.execute(
            query,
            (
                index_symbol,
                expiry_date,
                trading_date,
                atm_strike,
            ),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def _straddle_price(
        self,
        row: Dict[str, Any],
    ) -> float:
        return safe_float(
            row.get("straddle")
            or row.get("straddle_close")
        )

    def _bar_high(
        self,
        row: Dict[str, Any],
    ) -> float:
        return safe_float(
            row.get("straddle_high"),
            self._straddle_price(row),
        )

    def _bar_low(
        self,
        row: Dict[str, Any],
    ) -> float:
        return safe_float(
            row.get("straddle_low"),
            self._straddle_price(row),
        )

    def _volume(
        self,
        row: Dict[str, Any],
    ) -> int:
        return safe_int(
            row.get("combined_volume")
            or row.get("volume")
        )

    def _reference_0921(
        self,
        *,
        index_symbol: str,
        expiry_date: str,
        trading_date: str,
        rows: Sequence[Dict[str, Any]],
    ) -> float:
        if self._table_exists(
            "reference_locks"
        ):
            columns = self._columns(
                "reference_locks"
            )

            value_column = (
                "straddle"
                if "straddle" in columns
                else "straddle_close"
            )

            row = self.connection.execute(
                f"""
                SELECT {value_column} AS value
                FROM reference_locks
                WHERE trading_date = ?
                  AND index_symbol = ?
                  AND expiry_date = ?
                  AND reference_type IN (
                      'BATTLE_0921',
                      'REFERENCE_0921'
                  )
                ORDER BY lock_time
                LIMIT 1
                """,
                (
                    trading_date,
                    index_symbol,
                    expiry_date,
                ),
            ).fetchone()

            if row:
                value = safe_float(
                    row["value"]
                )

                if value > 0:
                    return value

        candidates = []

        for item in rows:
            timestamp = parse_timestamp(
                str(item["timestamp"])
            )

            distance = abs(
                (
                    timestamp.hour * 60
                    + timestamp.minute
                )
                - (
                    REFERENCE_TIME.hour * 60
                    + REFERENCE_TIME.minute
                )
            )

            candidates.append(
                (
                    distance,
                    self._straddle_price(item),
                )
            )

        if not candidates:
            return 0.0

        return min(
            candidates,
            key=lambda item: item[0],
        )[1]

    def _opening_range(
        self,
        rows: Sequence[Dict[str, Any]],
        latest_timestamp: datetime,
    ) -> Dict[str, Any]:
        range_rows = []

        for row in rows:
            timestamp = parse_timestamp(
                str(row["timestamp"])
            )
            row_time = timestamp.time().replace(
                tzinfo=None
            )

            if (
                OPENING_RANGE_START
                <= row_time
                < OPENING_RANGE_END
            ):
                range_rows.append(row)

        opening_range_ready = (
            latest_timestamp.time().replace(
                tzinfo=None
            )
            >= OPENING_RANGE_END
            and bool(range_rows)
        )

        if not range_rows:
            return {
                "ready": False,
                "high": 0.0,
                "low": 0.0,
                "width": 0.0,
            }

        high = max(
            self._bar_high(row)
            for row in range_rows
        )
        low = min(
            self._bar_low(row)
            for row in range_rows
        )

        return {
            "ready": opening_range_ready,
            "high": high,
            "low": low,
            "width": high - low,
        }

    def _vwap(
        self,
        rows: Sequence[Dict[str, Any]],
    ) -> float:
        weighted_sum = 0.0
        weight_sum = 0.0
        previous_volume = 0

        for row in rows:
            price = self._straddle_price(row)
            cumulative_volume = self._volume(row)

            volume_delta = max(
                cumulative_volume
                - previous_volume,
                0,
            )

            if volume_delta <= 0:
                volume_delta = 1

            weighted_sum += (
                price * volume_delta
            )
            weight_sum += volume_delta

            previous_volume = max(
                previous_volume,
                cumulative_volume,
            )

        if weight_sum <= 0:
            return 0.0

        return weighted_sum / weight_sum

    def _ema_envelope(
        self,
        rows: Sequence[Dict[str, Any]],
    ) -> Dict[str, float]:
        highs = [
            self._bar_high(row)
            for row in rows
        ]
        lows = [
            self._bar_low(row)
            for row in rows
        ]

        return {
            "high": ema(
                highs,
                EMA_PERIOD,
            ),
            "low": ema(
                lows,
                EMA_PERIOD,
            ),
        }

    def _continuous_decay(
        self,
        rows: Sequence[Dict[str, Any]],
        opening_range_low: float,
    ) -> bool:
        if len(rows) < DECAY_CONFIRMATION_BARS:
            return False

        recent = list(
            rows[-DECAY_CONFIRMATION_BARS:]
        )

        closes = [
            self._straddle_price(row)
            for row in recent
        ]

        below_range = all(
            close < opening_range_low
            for close in closes
        )

        descending = all(
            closes[index]
            <= closes[index - 1]
            for index in range(
                1,
                len(closes),
            )
        )

        return below_range and descending

    def analyse(
        self,
        index_symbol: str,
        expiry_date: Optional[str] = None,
    ) -> StraddleStructureReport:
        summary = self._latest_summary(
            index_symbol,
            expiry_date,
        )

        expiry = str(
            summary["expiry_date"]
        )
        trading_date = str(
            summary["trading_date"]
        )
        atm_strike = safe_int(
            summary["atm_strike"]
        )

        rows = self._session_rows(
            index_symbol,
            expiry,
            trading_date,
            atm_strike,
        )

        if not rows:
            raise RuntimeError(
                f"No ATM straddle history for "
                f"{index_symbol} {atm_strike}"
            )

        latest_row = rows[-1]
        latest_timestamp = parse_timestamp(
            str(latest_row["timestamp"])
        )
        current = self._straddle_price(
            latest_row
        )

        reference = self._reference_0921(
            index_symbol=index_symbol,
            expiry_date=expiry,
            trading_date=trading_date,
            rows=rows,
        )

        opening_range = self._opening_range(
            rows,
            latest_timestamp,
        )

        straddle_vwap = self._vwap(
            rows
        )
        envelope = self._ema_envelope(
            rows
        )

        or_high = safe_float(
            opening_range["high"]
        )
        or_low = safe_float(
            opening_range["low"]
        )
        ema_high = safe_float(
            envelope["high"]
        )
        ema_low = safe_float(
            envelope["low"]
        )

        above_orh = (
            opening_range["ready"]
            and current > or_high
        )
        below_orl = (
            opening_range["ready"]
            and current < or_low
        )
        above_vwap = (
            straddle_vwap > 0
            and current > straddle_vwap
        )
        below_vwap = (
            straddle_vwap > 0
            and current < straddle_vwap
        )
        above_ema_high = (
            ema_high > 0
            and current > ema_high
        )
        below_ema_low = (
            ema_low > 0
            and current < ema_low
        )
        inside_or = (
            opening_range["ready"]
            and or_low <= current <= or_high
        )
        inside_ema = (
            ema_low > 0
            and ema_high > 0
            and ema_low <= current <= ema_high
        )

        continuous_decay = (
            opening_range["ready"]
            and self._continuous_decay(
                rows,
                or_low,
            )
        )

        reasons: List[str] = []
        warnings: List[str] = []

        if not opening_range["ready"]:
            structure_state = (
                "OPENING_RANGE_NOT_READY"
            )
            straddle_bias = "NEUTRAL"
            short_stance = "WAIT"
            theta_state = "UNCONFIRMED"
            gamma_state = "UNCONFIRMED"
            confidence = 0.0

            reasons.append(
                "15-minute opening range is not complete"
            )

        elif (
            below_orl
            and continuous_decay
        ):
            structure_state = (
                "DECAY_BREAKDOWN"
            )
            straddle_bias = (
                "SHORT_STRADDLE"
            )
            short_stance = (
                "FAVOURABLE"
            )
            theta_state = "WINNING"
            gamma_state = "WEAK"
            confidence = 78.0

            reasons.append(
                "Straddle is below opening-range low"
            )
            reasons.append(
                f"{DECAY_CONFIRMATION_BARS} consecutive "
                f"closes confirm continuing decay"
            )

            if below_vwap:
                confidence += 8
                reasons.append(
                    "Straddle is below VWAP"
                )

            if below_ema_low:
                confidence += 8
                reasons.append(
                    "Straddle is below EMA75 low"
                )

        elif (
            above_orh
            and above_vwap
            and above_ema_high
        ):
            structure_state = (
                "EXPANSION_BREAKOUT"
            )
            straddle_bias = (
                "LONG_STRADDLE"
            )
            short_stance = "AVOID"
            theta_state = "LOSING"
            gamma_state = "BUILDING"
            confidence = 94.0

            reasons.append(
                "Straddle is above opening-range high"
            )
            reasons.append(
                "Straddle is above VWAP"
            )
            reasons.append(
                "Straddle is above EMA75 high"
            )
            warnings.append(
                "Fresh short straddle is structurally unfavourable"
            )

        elif (
            inside_or
            and inside_ema
        ):
            structure_state = (
                "STRUCTURAL_COMPRESSION"
            )
            straddle_bias = "NEUTRAL"
            short_stance = (
                "WAIT"
            )
            theta_state = "BALANCED"
            gamma_state = "DORMANT"
            confidence = 72.0

            reasons.append(
                "Straddle is inside the opening range"
            )
            reasons.append(
                "Straddle is inside EMA75 high/low envelope"
            )

            if above_vwap:
                reasons.append(
                    "Compression has upward pressure above VWAP"
                )
            elif below_vwap:
                reasons.append(
                    "Compression has downward pressure below VWAP"
                )
            else:
                reasons.append(
                    "Compression is balanced near VWAP"
                )

        elif below_orl:
            structure_state = (
                "DECAY_BREAKDOWN_UNCONFIRMED"
            )
            straddle_bias = (
                "SHORT_STRADDLE"
            )
            short_stance = (
                "WATCH"
            )
            theta_state = "BUILDING"
            gamma_state = "WEAKENING"
            confidence = 55.0

            reasons.append(
                "Straddle has moved below opening-range low"
            )
            warnings.append(
                "Continuous decay confirmation is pending"
            )

        elif above_orh:
            structure_state = (
                "EXPANSION_BREAKOUT_UNCONFIRMED"
            )
            straddle_bias = (
                "LONG_STRADDLE"
            )
            short_stance = "AVOID"
            theta_state = "AT_RISK"
            gamma_state = "BUILDING"
            confidence = 60.0

            reasons.append(
                "Straddle has moved above opening-range high"
            )

            if not above_vwap:
                warnings.append(
                    "VWAP confirmation is missing"
                )

            if not above_ema_high:
                warnings.append(
                    "EMA75 high confirmation is missing"
                )

        else:
            structure_state = (
                "TRANSITION"
            )
            straddle_bias = "NEUTRAL"
            short_stance = "WAIT"
            theta_state = "MIXED"
            gamma_state = "MIXED"
            confidence = 40.0

            reasons.append(
                "Straddle structure is not fully aligned"
            )

        confidence = max(
            0.0,
            min(confidence, 100.0),
        )

        columns = self._columns(
            self._straddle_table
        )

        has_true_ohlc = {
            "straddle_high",
            "straddle_low",
        }.issubset(columns)

        data_quality = (
            "TRUE_1M_OHLC"
            if has_true_ohlc
            else "CLOSE_BASED_SYNTHETIC"
        )

        if not has_true_ohlc:
            warnings.append(
                "OR and EMA envelope use 1-minute straddle "
                "samples because true straddle high/low fields "
                "are not yet stored"
            )

        change = current - reference
        change_pct = (
            (change / reference) * 100
            if reference > 0
            else 0.0
        )

        return StraddleStructureReport(
            index_symbol=index_symbol,
            expiry_date=expiry,
            trading_date=trading_date,
            timestamp=str(
                latest_row["timestamp"]
            ),
            atm_strike=atm_strike,

            reference_0921=round(
                reference,
                2,
            ),
            current_straddle=round(
                current,
                2,
            ),
            change_vs_0921=round(
                change,
                2,
            ),
            change_vs_0921_pct=round(
                change_pct,
                2,
            ),

            opening_range_ready=bool(
                opening_range["ready"]
            ),
            opening_range_high=round(
                or_high,
                2,
            ),
            opening_range_low=round(
                or_low,
                2,
            ),
            opening_range_width=round(
                safe_float(
                    opening_range["width"]
                ),
                2,
            ),

            straddle_vwap=round(
                straddle_vwap,
                2,
            ),
            ema75_high=round(
                ema_high,
                2,
            ),
            ema75_low=round(
                ema_low,
                2,
            ),

            above_orh=above_orh,
            below_orl=below_orl,
            above_vwap=above_vwap,
            below_vwap=below_vwap,
            above_ema75_high=(
                above_ema_high
            ),
            below_ema75_low=(
                below_ema_low
            ),
            inside_opening_range=(
                inside_or
            ),
            inside_ema_envelope=(
                inside_ema
            ),

            structure_state=(
                structure_state
            ),
            straddle_bias=(
                straddle_bias
            ),
            short_straddle_stance=(
                short_stance
            ),
            theta_state=theta_state,
            gamma_state=gamma_state,
            confidence=round(
                confidence,
                2,
            ),

            data_quality=data_quality,
            reasons=reasons,
            warnings=warnings,
        )


def print_straddle_structure(
    report: StraddleStructureReport,
    width: int = 100,
) -> None:
    print("\n" + "=" * width)
    print(
        "09:21 STRADDLE STRUCTURE ENGINE".center(
            width
        )
    )
    print("=" * width)

    print(
        f"INDEX                     : "
        f"{report.index_symbol}"
    )
    print(
        f"ATM STRIKE                : "
        f"{report.atm_strike}"
    )
    print(
        f"09:21 REFERENCE           : "
        f"₹{report.reference_0921:.2f}"
    )
    print(
        f"CURRENT STRADDLE          : "
        f"₹{report.current_straddle:.2f}"
    )
    print(
        f"CHANGE VS 09:21           : "
        f"{report.change_vs_0921:+.2f} "
        f"({report.change_vs_0921_pct:+.2f}%)"
    )

    print("-" * width)

    print(
        f"15M OR HIGH               : "
        f"₹{report.opening_range_high:.2f}"
    )
    print(
        f"15M OR LOW                : "
        f"₹{report.opening_range_low:.2f}"
    )
    print(
        f"STRADDLE VWAP             : "
        f"₹{report.straddle_vwap:.2f}"
    )
    print(
        f"EMA75 HIGH                : "
        f"₹{report.ema75_high:.2f}"
    )
    print(
        f"EMA75 LOW                 : "
        f"₹{report.ema75_low:.2f}"
    )

    print("-" * width)

    print(
        f"STRUCTURE STATE           : "
        f"{report.structure_state}"
    )
    print(
        f"STRADDLE BIAS             : "
        f"{report.straddle_bias}"
    )
    print(
        f"SHORT STRADDLE STANCE     : "
        f"{report.short_straddle_stance}"
    )
    print(
        f"THETA STATE               : "
        f"{report.theta_state}"
    )
    print(
        f"GAMMA STATE               : "
        f"{report.gamma_state}"
    )
    print(
        f"CONFIDENCE                : "
        f"{report.confidence:.2f}%"
    )
    print(
        f"DATA QUALITY              : "
        f"{report.data_quality}"
    )

    print("-" * width)
    print("WHY")

    for reason in report.reasons:
        print(f"✓ {reason}")

    if report.warnings:
        print("-" * width)
        print("WARNINGS")

        for warning in report.warnings:
            print(f"! {warning}")

    print("=" * width)
