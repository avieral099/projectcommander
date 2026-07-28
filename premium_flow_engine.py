"""
OPERATION COMMANDER
Module  : Premium Flow Engine V1
Purpose : ATM erosion, CE/PE premium migration, strike leadership,
          flow direction aur actionable premium-flow interpretation.

Reads from Premium Intelligence V2 database:
- option_minute_bars
- intelligence_summaries

Important:
Every label is returned with the actual strike.
Example:
    OTM1 CALL — 25200 CE
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


DEFAULT_DB_PATH = "premium_intelligence_1m.db"


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


def clamp(value: float) -> float:
    return max(0.0, min(float(value), 100.0))


def side_name(option_type: str) -> str:
    return "CALL" if option_type == "CE" else "PUT"


@dataclass(frozen=True)
class StrikeFlow:
    ladder_label: str
    strike: int
    option_type: str
    display_name: str
    current_ltp: float
    previous_ltp: float
    ltp_change: float
    ltp_change_pct: float
    volume: int
    oi: int
    flow_score: float


@dataclass(frozen=True)
class PremiumFlowReport:
    index_symbol: str
    expiry_date: str
    timestamp: str
    atm_strike: int

    atm_ce_strike: int
    atm_pe_strike: int
    atm_ce_erosion_pct: float
    atm_pe_erosion_pct: float
    dominant_atm_erosion: str

    call_leader_label: str
    call_leader_strike: int
    call_leader_display: str
    call_flow_score: float

    put_leader_label: str
    put_leader_strike: int
    put_leader_display: str
    put_flow_score: float

    dominant_side: str
    dominant_flow: str
    migration_speed: str
    migration_confidence: float

    atm_erosion_destination: str
    commander_interpretation: str

    call_heatmap: List[Dict[str, Any]]
    put_heatmap: List[Dict[str, Any]]
    reasons: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PremiumFlowEngine:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Premium intelligence database not found: {self.db_path}"
            )

        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

    def __enter__(self) -> "PremiumFlowEngine":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def _latest_summary(
        self,
        index_symbol: str,
        expiry_date: Optional[str] = None,
    ) -> Dict[str, Any]:
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
                (index_symbol, expiry_date),
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
                f"No premium intelligence summary available for {index_symbol}"
            )

        return dict(row)

    def _latest_option_rows(
        self,
        index_symbol: str,
        expiry_date: str,
        timestamp: str,
    ) -> List[Dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT *
            FROM option_minute_bars
            WHERE index_symbol = ?
              AND expiry_date = ?
              AND timestamp = ?
            ORDER BY option_type, strike
            """,
            (index_symbol, expiry_date, timestamp),
        ).fetchall()

        return [dict(row) for row in rows]

    def _previous_option_row(
        self,
        option_symbol: str,
        timestamp: str,
    ) -> Optional[Dict[str, Any]]:
        row = self.connection.execute(
            """
            SELECT *
            FROM option_minute_bars
            WHERE option_symbol = ?
              AND timestamp < ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (option_symbol, timestamp),
        ).fetchone()

        return dict(row) if row else None

    def _build_strike_flows(
        self,
        rows: Sequence[Dict[str, Any]],
        timestamp: str,
    ) -> List[StrikeFlow]:
        output: List[StrikeFlow] = []

        for row in rows:
            current_ltp = safe_float(row.get("ltp"))
            previous_row = self._previous_option_row(
                str(row.get("option_symbol")),
                timestamp,
            )

            previous_ltp = (
                safe_float(previous_row.get("ltp"))
                if previous_row
                else safe_float(row.get("previous_close"), current_ltp)
            )

            ltp_change = current_ltp - previous_ltp
            ltp_change_pct = (
                (ltp_change / previous_ltp) * 100
                if previous_ltp > 0
                else 0.0
            )

            volume = safe_int(row.get("volume"))
            oi = safe_int(row.get("oi"))
            ladder_label = str(row.get("ladder_label"))
            option_type = str(row.get("option_type"))
            strike = safe_int(row.get("strike"))

            momentum_component = max(ltp_change_pct, 0.0) * 8
            volume_component = min(volume / 5000, 20)
            oi_component = min(oi / 25000, 15)

            distance_bonus = 0.0

            if ladder_label.startswith("OTM"):
                distance = safe_int(
                    ladder_label.replace("OTM", "").replace("_CE", "").replace("_PE", "")
                )
                distance_bonus = min(distance * 5, 15)

            flow_score = clamp(
                momentum_component
                + volume_component
                + oi_component
                + distance_bonus
            )

            output.append(
                StrikeFlow(
                    ladder_label=ladder_label,
                    strike=strike,
                    option_type=option_type,
                    display_name=(
                        f"{ladder_label.replace('_CE', '').replace('_PE', '')} "
                        f"{side_name(option_type)} — {strike} {option_type}"
                    ),
                    current_ltp=round(current_ltp, 2),
                    previous_ltp=round(previous_ltp, 2),
                    ltp_change=round(ltp_change, 2),
                    ltp_change_pct=round(ltp_change_pct, 2),
                    volume=volume,
                    oi=oi,
                    flow_score=round(flow_score, 2),
                )
            )

        return output

    def _leader(
        self,
        flows: Sequence[StrikeFlow],
        option_type: str,
    ) -> Optional[StrikeFlow]:
        candidates = [
            item
            for item in flows
            if item.option_type == option_type
        ]

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda item: (
                item.flow_score,
                item.ltp_change_pct,
                item.volume,
            ),
        )

    def _atm_flow(
        self,
        flows: Sequence[StrikeFlow],
        option_type: str,
    ) -> Optional[StrikeFlow]:
        for item in flows:
            if (
                item.option_type == option_type
                and item.ladder_label.startswith("ATM")
            ):
                return item

        return None

    def _migration_speed(
        self,
        leader: Optional[StrikeFlow],
    ) -> str:
        if not leader:
            return "DATA_NOT_READY"

        score = leader.flow_score
        change = leader.ltp_change_pct

        if score >= 80 or change >= 12:
            return "EXPLOSIVE"

        if score >= 60 or change >= 7:
            return "FAST"

        if score >= 35 or change >= 3:
            return "MODERATE"

        return "SLOW"

    def _heatmap(
        self,
        flows: Sequence[StrikeFlow],
        option_type: str,
    ) -> List[Dict[str, Any]]:
        side_flows = [
            item
            for item in flows
            if item.option_type == option_type
        ]

        if not side_flows:
            return []

        maximum = max(
            item.flow_score
            for item in side_flows
        ) or 1.0

        output = []

        for item in sorted(
            side_flows,
            key=lambda x: x.strike,
        ):
            bars = max(
                1,
                round(
                    (item.flow_score / maximum) * 20
                ),
            )

            output.append(
                {
                    "label": item.ladder_label,
                    "strike": item.strike,
                    "option_type": item.option_type,
                    "display_name": item.display_name,
                    "flow_score": item.flow_score,
                    "ltp_change_pct": item.ltp_change_pct,
                    "bar": "█" * bars,
                }
            )

        return output

    def analyse(
        self,
        index_symbol: str,
        expiry_date: Optional[str] = None,
    ) -> PremiumFlowReport:
        summary = self._latest_summary(
            index_symbol,
            expiry_date,
        )

        expiry = str(summary["expiry_date"])
        timestamp = str(summary["timestamp"])
        atm_strike = safe_int(
            summary.get("atm_strike")
        )

        rows = self._latest_option_rows(
            index_symbol,
            expiry,
            timestamp,
        )

        if not rows:
            raise RuntimeError(
                "No option-minute rows available for latest intelligence timestamp"
            )

        flows = self._build_strike_flows(
            rows,
            timestamp,
        )

        call_leader = self._leader(
            flows,
            "CE",
        )
        put_leader = self._leader(
            flows,
            "PE",
        )

        atm_ce = self._atm_flow(
            flows,
            "CE",
        )
        atm_pe = self._atm_flow(
            flows,
            "PE",
        )

        atm_ce_erosion = (
            -atm_ce.ltp_change_pct
            if atm_ce
            and atm_ce.ltp_change_pct < 0
            else 0.0
        )

        atm_pe_erosion = (
            -atm_pe.ltp_change_pct
            if atm_pe
            and atm_pe.ltp_change_pct < 0
            else 0.0
        )

        dominant_atm_erosion = (
            "CALL_ATM_EROSION"
            if atm_ce_erosion > atm_pe_erosion
            else "PUT_ATM_EROSION"
            if atm_pe_erosion > atm_ce_erosion
            else "BALANCED_ATM_EROSION"
        )

        call_score = (
            call_leader.flow_score
            if call_leader
            else 0.0
        )

        put_score = (
            put_leader.flow_score
            if put_leader
            else 0.0
        )

        if call_score > put_score:
            dominant_side = "CALL"
            dominant_leader = call_leader
        elif put_score > call_score:
            dominant_side = "PUT"
            dominant_leader = put_leader
        else:
            dominant_side = "BALANCED"
            dominant_leader = None

        if not dominant_leader:
            dominant_flow = "CENTRED"
        elif dominant_leader.ladder_label.startswith("OTM"):
            dominant_flow = (
                f"{dominant_side}_OTM_MIGRATION"
            )
        elif dominant_leader.ladder_label.startswith("ITM"):
            dominant_flow = (
                f"{dominant_side}_ITM_MIGRATION"
            )
        else:
            dominant_flow = (
                f"{dominant_side}_ATM_CENTRED"
            )

        speed = self._migration_speed(
            dominant_leader
        )

        confidence = clamp(
            abs(call_score - put_score)
            + max(call_score, put_score) * 0.45
        )

        erosion_destination = "NOT_DETECTED"

        if dominant_leader:
            if dominant_side == "CALL" and atm_ce_erosion > 0:
                erosion_destination = (
                    f"ATM CALL {atm_ce.strike} CE → "
                    f"{dominant_leader.display_name}"
                )
            elif dominant_side == "PUT" and atm_pe_erosion > 0:
                erosion_destination = (
                    f"ATM PUT {atm_pe.strike} PE → "
                    f"{dominant_leader.display_name}"
                )

        if (
            dominant_side == "CALL"
            and dominant_leader
            and dominant_leader.ladder_label.startswith("OTM")
        ):
            interpretation = (
                f"CALL premium is migrating away from ATM "
                f"toward {dominant_leader.display_name}. "
                f"ATM call erosion is being replaced by OTM call expansion."
            )

        elif (
            dominant_side == "PUT"
            and dominant_leader
            and dominant_leader.ladder_label.startswith("OTM")
        ):
            interpretation = (
                f"PUT premium is migrating away from ATM "
                f"toward {dominant_leader.display_name}. "
                f"ATM put erosion is being replaced by OTM put expansion."
            )

        elif dominant_side == "BALANCED":
            interpretation = (
                "CALL and PUT premium flow are balanced. "
                "No clean migration leader."
            )

        else:
            interpretation = (
                f"Premium leadership remains near "
                f"{dominant_leader.display_name if dominant_leader else 'ATM'}."
            )

        reasons = []

        if call_leader:
            reasons.append(
                f"Call leader: {call_leader.display_name} "
                f"[{call_leader.flow_score:.2f}]"
            )

        if put_leader:
            reasons.append(
                f"Put leader: {put_leader.display_name} "
                f"[{put_leader.flow_score:.2f}]"
            )

        reasons.append(
            f"ATM CE erosion: {atm_ce_erosion:.2f}% "
            f"at {atm_ce.strike if atm_ce else 0} CE"
        )
        reasons.append(
            f"ATM PE erosion: {atm_pe_erosion:.2f}% "
            f"at {atm_pe.strike if atm_pe else 0} PE"
        )

        warnings = []

        if speed in {"FAST", "EXPLOSIVE"}:
            warnings.append(
                "Rapid premium migration detected"
            )

        if dominant_side == "BALANCED":
            warnings.append(
                "No directional premium edge"
            )

        return PremiumFlowReport(
            index_symbol=index_symbol,
            expiry_date=expiry,
            timestamp=timestamp,
            atm_strike=atm_strike,

            atm_ce_strike=(
                atm_ce.strike
                if atm_ce
                else 0
            ),
            atm_pe_strike=(
                atm_pe.strike
                if atm_pe
                else 0
            ),
            atm_ce_erosion_pct=round(
                atm_ce_erosion,
                2,
            ),
            atm_pe_erosion_pct=round(
                atm_pe_erosion,
                2,
            ),
            dominant_atm_erosion=(
                dominant_atm_erosion
            ),

            call_leader_label=(
                call_leader.ladder_label
                if call_leader
                else "NOT_AVAILABLE"
            ),
            call_leader_strike=(
                call_leader.strike
                if call_leader
                else 0
            ),
            call_leader_display=(
                call_leader.display_name
                if call_leader
                else "NOT AVAILABLE"
            ),
            call_flow_score=round(
                call_score,
                2,
            ),

            put_leader_label=(
                put_leader.ladder_label
                if put_leader
                else "NOT_AVAILABLE"
            ),
            put_leader_strike=(
                put_leader.strike
                if put_leader
                else 0
            ),
            put_leader_display=(
                put_leader.display_name
                if put_leader
                else "NOT AVAILABLE"
            ),
            put_flow_score=round(
                put_score,
                2,
            ),

            dominant_side=dominant_side,
            dominant_flow=dominant_flow,
            migration_speed=speed,
            migration_confidence=round(
                confidence,
                2,
            ),

            atm_erosion_destination=(
                erosion_destination
            ),
            commander_interpretation=(
                interpretation
            ),

            call_heatmap=self._heatmap(
                flows,
                "CE",
            ),
            put_heatmap=self._heatmap(
                flows,
                "PE",
            ),
            reasons=reasons,
            warnings=warnings,
        )


def print_premium_flow(
    report: PremiumFlowReport,
    width: int = 100,
) -> None:
    print("\n" + "=" * width)
    print(
        "PREMIUM FLOW ENGINE V1".center(
            width
        )
    )
    print("=" * width)

    print(
        f"ATM STRIKE                : "
        f"{report.atm_strike}"
    )
    print(
        f"ATM CALL                  : "
        f"{report.atm_ce_strike} CE | "
        f"EROSION {report.atm_ce_erosion_pct:.2f}%"
    )
    print(
        f"ATM PUT                   : "
        f"{report.atm_pe_strike} PE | "
        f"EROSION {report.atm_pe_erosion_pct:.2f}%"
    )

    print("-" * width)

    print(
        f"CALL PREMIUM LEADER       : "
        f"{report.call_leader_display}"
    )
    print(
        f"CALL FLOW SCORE           : "
        f"{report.call_flow_score:.2f}"
    )
    print(
        f"PUT PREMIUM LEADER        : "
        f"{report.put_leader_display}"
    )
    print(
        f"PUT FLOW SCORE            : "
        f"{report.put_flow_score:.2f}"
    )

    print("-" * width)

    print(
        f"DOMINANT SIDE             : "
        f"{report.dominant_side}"
    )
    print(
        f"DOMINANT FLOW             : "
        f"{report.dominant_flow}"
    )
    print(
        f"MIGRATION SPEED           : "
        f"{report.migration_speed}"
    )
    print(
        f"MIGRATION CONFIDENCE      : "
        f"{report.migration_confidence:.2f}%"
    )
    print(
        f"ATM EROSION DESTINATION   : "
        f"{report.atm_erosion_destination}"
    )

    print("-" * width)

    print("CALL HEATMAP")
    for item in report.call_heatmap:
        print(
            f"{item['display_name']:<28} "
            f"{item['bar']} "
            f"{item['flow_score']:.2f}"
        )

    print("-" * width)

    print("PUT HEATMAP")
    for item in report.put_heatmap:
        print(
            f"{item['display_name']:<28} "
            f"{item['bar']} "
            f"{item['flow_score']:.2f}"
        )

    print("-" * width)

    print(
        f"COMMANDER INTERPRETATION  : "
        f"{report.commander_interpretation}"
    )

    print("=" * width)
