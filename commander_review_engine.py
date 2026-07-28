from __future__ import annotations

import argparse
import csv
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

DEFAULT_DB = "premium_intelligence_1m.db"
DEFAULT_TABLE = "intelligence_summaries"


@dataclass(frozen=True)
class Row:
    timestamp: str
    trading_date: str
    index_symbol: str
    spot_price: float
    atm_straddle: float
    change_1m_pct: float
    change_from_open_pct: float
    change_vs_0921_pct: float
    change_vs_0925_pct: float
    premium_remaining_pct: float
    rotation_count: int
    net_shift_points: int
    decay_state: str
    rotation_state: str
    commander_state: str
    premium_flow_side: str
    straddle_structure: str
    straddle_bias: str
    battle_status: str
    battle_score: float
    evidence_verdict: str
    evidence_score: float
    call_confidence: float
    put_confidence: float
    engine_agreement: int


def _f(v: Any) -> float:
    try:
        return float(v or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _i(v: Any) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _ts(v: str) -> datetime:
    return datetime.fromisoformat(v)


def _side(verdict: str) -> str:
    value = (verdict or "").upper()
    if "CALL" in value:
        return "CALL"
    if "PUT" in value:
        return "PUT"
    return "NEUTRAL"


def load_rows(db_path: str | Path, trading_date: str) -> list[Row]:
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    sql = f"""
    SELECT timestamp,trading_date,index_symbol,spot_price,atm_straddle,
           change_1m_pct,change_from_open_pct,change_vs_0921_pct,
           change_vs_0925_pct,premium_remaining_pct,rotation_count,
           net_shift_points,decay_state,rotation_state,commander_state,
           premium_flow_side,straddle_structure,straddle_bias,battle_status,
           battle_score,evidence_verdict,evidence_score,call_confidence,
           put_confidence,engine_agreement
    FROM {DEFAULT_TABLE}
    WHERE trading_date=?
    ORDER BY index_symbol,timestamp
    """

    out: list[Row] = []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for r in conn.execute(sql, (trading_date,)):
            out.append(Row(
                str(r["timestamp"]), str(r["trading_date"]), str(r["index_symbol"]),
                _f(r["spot_price"]), _f(r["atm_straddle"]), _f(r["change_1m_pct"]),
                _f(r["change_from_open_pct"]), _f(r["change_vs_0921_pct"]),
                _f(r["change_vs_0925_pct"]), _f(r["premium_remaining_pct"]),
                _i(r["rotation_count"]), _i(r["net_shift_points"]),
                str(r["decay_state"] or "UNKNOWN"),
                str(r["rotation_state"] or "UNKNOWN"),
                str(r["commander_state"] or "UNKNOWN"),
                str(r["premium_flow_side"] or "BALANCED"),
                str(r["straddle_structure"] or "UNKNOWN"),
                str(r["straddle_bias"] or "NEUTRAL"),
                str(r["battle_status"] or "UNKNOWN"),
                _f(r["battle_score"]),
                str(r["evidence_verdict"] or "NO_BIAS"),
                _f(r["evidence_score"]), _f(r["call_confidence"]),
                _f(r["put_confidence"]), _i(r["engine_agreement"]),
            ))
    return out


def future_row(rows: list[Row], idx: int, minutes: int) -> Optional[Row]:
    target = _ts(rows[idx].timestamp) + timedelta(minutes=minutes)
    for row in rows[idx + 1:]:
        if _ts(row.timestamp) >= target:
            return row
    return None


def score(current: Row, future: Optional[Row]) -> tuple[str, str]:
    if future is None:
        return "UNSCORED", "No future row"

    move = future.spot_price - current.spot_price
    side = _side(current.evidence_verdict)
    flat_threshold = max(current.spot_price * 0.0005, 1.0)

    if side == "CALL":
        if move > 0:
            return "CORRECT", f"Spot {move:+.2f}"
        if abs(move) <= flat_threshold:
            return "NEUTRAL", f"Spot nearly flat {move:+.2f}"
        return "WRONG", f"Spot {move:+.2f}"

    if side == "PUT":
        if move < 0:
            return "CORRECT", f"Spot {move:+.2f}"
        if abs(move) <= flat_threshold:
            return "NEUTRAL", f"Spot nearly flat {move:+.2f}"
        return "WRONG", f"Spot {move:+.2f}"

    pct = abs(move) / current.spot_price * 100 if current.spot_price else 0
    if pct <= 0.15:
        return "CORRECT", f"Neutral; move only {pct:.2f}%"
    return "MISSED", f"Neutral missed {move:+.2f} ({pct:.2f}%)"


def transitions(rows: list[Row]) -> list[str]:
    fields = (
        "commander_state","battle_status","evidence_verdict","premium_flow_side",
        "rotation_state","decay_state","straddle_structure","straddle_bias",
    )
    result: list[str] = []
    for prev, cur in zip(rows, rows[1:]):
        changes = []
        for field in fields:
            a, b = getattr(prev, field), getattr(cur, field)
            if a != b:
                changes.append(f"{field}: {a} -> {b}")
        if changes:
            result.append(f"{cur.timestamp} | " + "; ".join(changes))
    return result


def render_report(trading_date: str, grouped: dict[str, list[Row]], horizon: int) -> str:
    width = 100
    lines = [
        "=" * width,
        f"OPERATION COMMANDER — AUTOMATIC DECISION AUDIT — {trading_date}".center(width),
        "=" * width,
        f"Scoring horizon: {horizon} minutes",
        "",
    ]

    for symbol, rows in grouped.items():
        verdicts = Counter(r.evidence_verdict for r in rows)
        battles = Counter(r.battle_status for r in rows)
        flows = Counter(r.premium_flow_side for r in rows)

        scored = []
        for idx, row in enumerate(rows):
            outcome, detail = score(row, future_row(rows, idx, horizon))
            scored.append((row, outcome, detail))
        outcomes = Counter(x[1] for x in scored)
        denom = sum(outcomes[k] for k in ("CORRECT","WRONG","MISSED","NEUTRAL"))
        accuracy = outcomes["CORRECT"] / denom * 100 if denom else 0.0

        lines += [
            "-" * width,
            symbol.center(width),
            "-" * width,
            f"Rows: {len(rows)}",
            f"Period: {rows[0].timestamp} -> {rows[-1].timestamp}",
            f"Spot: {rows[0].spot_price:.2f} -> {rows[-1].spot_price:.2f}",
            f"Straddle: {rows[0].atm_straddle:.2f} -> {rows[-1].atm_straddle:.2f}",
            "Evidence: " + ", ".join(f"{k}={v}" for k, v in verdicts.most_common()),
            "Battle:   " + ", ".join(f"{k}={v}" for k, v in battles.most_common()),
            "Flow:     " + ", ".join(f"{k}={v}" for k, v in flows.most_common()),
            "Outcome:  " + ", ".join(f"{k}={v}" for k, v in outcomes.most_common()),
            f"Observation accuracy: {accuracy:.2f}%",
            "",
            "TOP WRONG / MISSED OBSERVATIONS",
        ]

        failures = [x for x in scored if x[1] in {"WRONG","MISSED"}]
        failures.sort(key=lambda x: max(x[0].call_confidence, x[0].put_confidence), reverse=True)
        if failures:
            for row, outcome, detail in failures[:15]:
                lines.append(
                    f"{row.timestamp} | {outcome} | {row.evidence_verdict} "
                    f"{row.evidence_score:.0f}% | {row.battle_status} | {detail}"
                )
        else:
            lines.append("None under current scoring rules.")

        lines += ["", "STATE TRANSITIONS"]
        trans = transitions(rows)
        lines.extend(trans[:30] if trans else ["No state transitions."])
        if len(trans) > 30:
            lines.append(f"... {len(trans)-30} more transitions")
        lines.append("")

    lines += [
        "=" * width,
        "NOTES",
        "=" * width,
        "This V1 audits recorded observations against later spot movement.",
        "It does not reconstruct actual option fills, slippage, brokerage or trade P&L.",
    ]
    return "\n".join(lines) + "\n"


def write_csv(path: Path, grouped: dict[str, list[Row]], horizon: int) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "timestamp","index_symbol","commander_state","battle_status",
            "evidence_verdict","evidence_score","call_confidence","put_confidence",
            "premium_flow_side","rotation_state","decay_state","straddle_structure",
            "straddle_bias","spot_price","atm_straddle",
            f"outcome_{horizon}m",f"outcome_detail_{horizon}m",
        ])
        for symbol, rows in grouped.items():
            for idx, row in enumerate(rows):
                outcome, detail = score(row, future_row(rows, idx, horizon))
                w.writerow([
                    row.timestamp,symbol,row.commander_state,row.battle_status,
                    row.evidence_verdict,row.evidence_score,row.call_confidence,
                    row.put_confidence,row.premium_flow_side,row.rotation_state,
                    row.decay_state,row.straddle_structure,row.straddle_bias,
                    row.spot_price,row.atm_straddle,outcome,detail,
                ])


def generate_report(db: str | Path, trading_date: str, horizon: int = 15, output_dir: str | Path = "."):
    rows = load_rows(db, trading_date)
    if not rows:
        raise RuntimeError(f"No rows found for {trading_date}")

    grouped: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        grouped[row.index_symbol].append(row)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = trading_date.replace("-", "")
    txt = out / f"commander_review_{stamp}.txt"
    csv_path = out / f"commander_review_{stamp}.csv"

    txt.write_text(render_report(trading_date, dict(grouped), horizon), encoding="utf-8")
    write_csv(csv_path, dict(grouped), horizon)
    return txt, csv_path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=DEFAULT_DB)
    p.add_argument("--date", required=True)
    p.add_argument("--horizon", type=int, default=15)
    p.add_argument("--output-dir", default=".")
    args = p.parse_args()
    if args.horizon <= 0:
        p.error("--horizon must be greater than zero")

    txt, csv_path = generate_report(args.db, args.date, args.horizon, args.output_dir)
    print("COMMANDER REVIEW GENERATED")
    print(f"TEXT: {txt}")
    print(f"CSV : {csv_path}")


if __name__ == "__main__":
    main()
