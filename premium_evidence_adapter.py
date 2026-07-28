from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


JSON_CANDIDATES = (
    "premium_snapshot.json",
    "premium_intelligence_snapshot.json",
    "premium_behaviour_snapshot.json",
    "commander_premium_snapshot.json",
    "options_straddle_snapshot.json",
    "live_cache.json",
)

DB_CANDIDATES = (
    "premium_intelligence_1m.db",
    "premium_intelligence.db",
)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalise_side(value: Any) -> str:
    text = str(value or "").upper()

    if any(token in text for token in ("CALL", "CE", "BULL", "UPWARD")):
        return "CALL"
    if any(token in text for token in ("PUT", "PE", "BEAR", "DOWNWARD")):
        return "PUT"
    if any(token in text for token in ("BALANCED", "NEUTRAL", "MIXED")):
        return "BALANCED"

    return "UNKNOWN"


def _first(mapping: dict[str, Any], names: Iterable[str], default: Any = None) -> Any:
    for name in names:
        if name in mapping and mapping[name] not in (None, ""):
            return mapping[name]
    return default


def _flatten_latest(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        for key in ("latest", "data", "premium", "summary", "result"):
            nested = value.get(key)
            if isinstance(nested, dict):
                merged = dict(value)
                merged.update(nested)
                return merged

        for key in ("rows", "records", "items", "summaries"):
            rows = value.get(key)
            if isinstance(rows, list) and rows and isinstance(rows[-1], dict):
                merged = dict(value)
                merged.update(rows[-1])
                return merged

        return value

    if isinstance(value, list) and value and isinstance(value[-1], dict):
        return value[-1]

    return {}


def _score_from_row(row: dict[str, Any], side: str) -> float:
    direct = _first(
        row,
        (
            "premium_score",
            "evidence_score",
            "confidence",
            "score",
        ),
    )
    if direct is not None:
        score = _number(direct)
        if 0 < score <= 1:
            score *= 100
        return max(0.0, min(100.0, score))

    call_conf = _number(_first(row, ("call_confidence", "call_score"), 0))
    put_conf = _number(_first(row, ("put_confidence", "put_score"), 0))

    if side == "CALL" and call_conf:
        return max(0.0, min(100.0, call_conf))
    if side == "PUT" and put_conf:
        return max(0.0, min(100.0, put_conf))

    strength = 0.0
    recognised = 0

    state_text = " ".join(
        str(_first(row, (key,), ""))
        for key in (
            "commander_state",
            "decay_state",
            "rotation_state",
            "straddle_structure",
            "premium_flow_side",
        )
    ).upper()

    for token, points in (
        ("PREMIUM_EXPANSION", 25),
        ("ROTATION_WITH_EXPANSION", 20),
        ("AGGRESSIVE", 15),
        ("FAST_DECAY", 10),
        ("DECAY_BREAKDOWN", 10),
        ("THETA_DOMINANT", 10),
        ("BALANCED", 5),
    ):
        if token in state_text:
            strength += points
            recognised += 1

    if side in {"CALL", "PUT"}:
        strength += 25
        recognised += 1

    if recognised == 0:
        return 0.0

    return max(0.0, min(100.0, strength))


def normalise_premium_evidence(
    row: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    side = _normalise_side(
        _first(
            row,
            (
                "premium_flow_side",
                "flow_side",
                "premium_side",
                "side",
                "evidence_verdict",
            ),
        )
    )

    commander_state = str(
        _first(
            row,
            (
                "commander_state",
                "premium_state",
                "premium_regime",
                "regime",
            ),
            "UNKNOWN",
        )
    ).upper()

    decay_state = str(
        _first(row, ("decay_state", "decay_status"), "UNKNOWN")
    ).upper()

    rotation_state = str(
        _first(row, ("rotation_state", "rotation"), "UNKNOWN")
    ).upper()

    straddle_structure = str(
        _first(
            row,
            (
                "straddle_structure",
                "straddle_state",
                "straddle_bias",
            ),
            "UNKNOWN",
        )
    ).upper()

    score = _score_from_row(row, side)

    timestamp = str(
        _first(
            row,
            (
                "timestamp",
                "updated_at",
                "generated_at",
                "time",
            ),
            datetime.now().isoformat(timespec="seconds"),
        )
    )

    index_symbol = str(
        _first(
            row,
            (
                "index_symbol",
                "symbol",
                "index",
            ),
            "UNKNOWN",
        )
    )

    missing = []
    if side == "UNKNOWN":
        missing.append("premium_flow_side")
    if commander_state == "UNKNOWN":
        missing.append("commander_state")
    if score <= 0:
        missing.append("premium_score")

    status = "CONNECTED" if not missing else "PARTIAL"

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_timestamp": timestamp,
        "source": source,
        "status": status,
        "index_symbol": index_symbol,
        "premium_flow_side": side,
        "premium_score": round(score, 2),
        "commander_state": commander_state,
        "decay_state": decay_state,
        "rotation_state": rotation_state,
        "straddle_structure": straddle_structure,
        "atm_straddle": _number(
            _first(row, ("atm_straddle", "straddle", "straddle_value"), 0)
        ),
        "spot_price": _number(
            _first(row, ("spot_price", "spot", "ltp"), 0)
        ),
        "call_confidence": _number(
            _first(row, ("call_confidence", "call_score"), 0)
        ),
        "put_confidence": _number(
            _first(row, ("put_confidence", "put_score"), 0)
        ),
        "missing_fields": missing,
        "raw_keys": sorted(row.keys()),
        "note": (
            "Premium Evidence Adapter V1 standardises existing Commander output. "
            "It does not invent missing premium evidence."
        ),
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        row = _flatten_latest(raw)
        return row or None
    except Exception:
        return None


def _table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    cursor = connection.execute(f'PRAGMA table_info("{table}")')
    return [str(row[1]) for row in cursor.fetchall()]


def _latest_db_row(path: Path) -> tuple[dict[str, Any] | None, str]:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row

    try:
        tables = [
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]

        preferred = (
            "intelligence_summaries",
            "premium_summaries",
            "premium_intelligence",
            "straddle_minute_bars",
            "option_minute_bars",
        )

        ordered = [name for name in preferred if name in tables]
        ordered.extend(name for name in tables if name not in ordered)

        for table in ordered:
            columns = _table_columns(connection, table)
            if not columns:
                continue

            order_column = next(
                (
                    name
                    for name in (
                        "timestamp",
                        "updated_at",
                        "created_at",
                        "id",
                    )
                    if name in columns
                ),
                None,
            )

            query = f'SELECT * FROM "{table}"'
            if order_column:
                query += f' ORDER BY "{order_column}" DESC'
            query += " LIMIT 1"

            try:
                result = connection.execute(query).fetchone()
            except sqlite3.Error:
                continue

            if result:
                return dict(result), table

        return None, ""
    finally:
        connection.close()


def discover_source(
    explicit_json: str | None = None,
    explicit_db: str | None = None,
) -> tuple[dict[str, Any], str]:
    if explicit_json:
        path = Path(explicit_json)
        row = _read_json(path)
        if row:
            return row, f"json:{path.name}"
        raise RuntimeError(f"Unable to read premium JSON: {path}")

    if explicit_db:
        path = Path(explicit_db)
        row, table = _latest_db_row(path)
        if row:
            return row, f"sqlite:{path.name}:{table}"
        raise RuntimeError(f"No usable premium row found in: {path}")

    for name in JSON_CANDIDATES:
        path = Path(name)
        if path.exists():
            row = _read_json(path)
            if row:
                return row, f"json:{path.name}"

    for name in DB_CANDIDATES:
        path = Path(name)
        if path.exists():
            row, table = _latest_db_row(path)
            if row:
                return row, f"sqlite:{path.name}:{table}"

    raise FileNotFoundError(
        "No premium source found. Checked JSON candidates and "
        "premium_intelligence_1m.db."
    )


def generate_premium_evidence(
    *,
    json_source: str | None = None,
    db_source: str | None = None,
    output_path: str = "premium_evidence_snapshot.json",
) -> dict[str, Any]:
    row, source = discover_source(json_source, db_source)
    result = normalise_premium_evidence(row, source=source)

    Path(output_path).write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-source")
    parser.add_argument("--db-source")
    parser.add_argument(
        "--output",
        default="premium_evidence_snapshot.json",
    )
    args = parser.parse_args()

    result = generate_premium_evidence(
        json_source=args.json_source,
        db_source=args.db_source,
        output_path=args.output,
    )

    print("PREMIUM EVIDENCE SNAPSHOT CREATED")
    print(f"SOURCE : {result['source']}")
    print(f"STATUS : {result['status']}")
    print(f"SIDE   : {result['premium_flow_side']}")
    print(f"SCORE  : {result['premium_score']}")
    print(f"OUTPUT : {args.output}")

    if result["missing_fields"]:
        print("MISSING: " + ", ".join(result["missing_fields"]))


if __name__ == "__main__":
    main()
