from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


JSON_CANDIDATES = (
    "driver_snapshot.json",
    "driver_engine_snapshot.json",
    "driver_evidence.json",
    "commander_driver_snapshot.json",
    "live_cache.json",
    "market_structure_snapshot.json",
)

DEFAULT_DRIVER_NAMES = (
    "NIFTYIT",
    "RELIANCE",
    "HDFCBANK",
    "ICICIBANK",
    "TCS",
    "INFY",
)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _first(mapping: dict[str, Any], names: Iterable[str], default: Any = None) -> Any:
    for name in names:
        if name in mapping and mapping[name] not in (None, ""):
            return mapping[name]
    return default


def _normalise_side(value: Any) -> str:
    text = str(value or "").upper()

    if any(token in text for token in ("BULL", "CALL", "UP", "POSITIVE", "GREEN", "STRONG")):
        return "BULL"
    if any(token in text for token in ("BEAR", "PUT", "DOWN", "NEGATIVE", "RED", "WEAK")):
        return "BEAR"
    if any(token in text for token in ("MIXED", "NEUTRAL", "BALANCED", "FLAT")):
        return "NEUTRAL"

    return "UNKNOWN"


def _flatten(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("latest", "data", "result", "summary", "drivers"):
            nested = value.get(key)
            if nested is not None:
                if isinstance(nested, (dict, list)):
                    return nested
        return value

    return value


def _extract_driver_rows(value: Any) -> list[dict[str, Any]]:
    value = _flatten(value)

    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]

    if not isinstance(value, dict):
        return []

    for key in (
        "driver_rows",
        "driver_data",
        "drivers",
        "components",
        "constituents",
        "items",
        "records",
        "rows",
    ):
        rows = value.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]

    rows: list[dict[str, Any]] = []

    for key, item in value.items():
        if isinstance(item, dict):
            item_copy = dict(item)
            item_copy.setdefault("symbol", key)
            rows.append(item_copy)

    return rows


def _driver_name(row: dict[str, Any]) -> str:
    return str(
        _first(
            row,
            (
                "symbol",
                "name",
                "driver",
                "index_symbol",
                "ticker",
            ),
            "UNKNOWN",
        )
    ).upper()


def _row_side(row: dict[str, Any]) -> str:
    direct = _first(
        row,
        (
            "driver_side",
            "side",
            "bias",
            "state",
            "status",
            "verdict",
            "direction",
        ),
    )
    side = _normalise_side(direct)
    if side != "UNKNOWN":
        return side

    score = _number(
        _first(
            row,
            (
                "change_pct",
                "change_percent",
                "pct_change",
                "change",
            ),
            0,
        )
    )

    if score > 0:
        return "BULL"
    if score < 0:
        return "BEAR"

    above_count = 0
    below_count = 0

    for key in (
        "above_pdc",
        "above_vwap",
        "above_orh",
        "above_pdh",
        "above_ema",
        "above_ema75",
    ):
        if row.get(key) is True:
            above_count += 1
        elif row.get(key) is False:
            below_count += 1

    if above_count > below_count:
        return "BULL"
    if below_count > above_count:
        return "BEAR"

    return "NEUTRAL"


def _row_score(row: dict[str, Any], side: str) -> float:
    direct = _first(
        row,
        (
            "driver_score",
            "score",
            "confidence",
            "strength",
            "agreement_pct",
        ),
    )

    if direct is not None:
        score = _number(direct)
        if 0 < score <= 1:
            score *= 100
        return max(0.0, min(100.0, score))

    checks = []
    for key in (
        "above_pdc",
        "above_vwap",
        "above_orh",
        "above_pdh",
        "above_ema",
        "above_ema75",
    ):
        if key in row:
            checks.append(bool(row[key]))

    if checks:
        positive = sum(1 for value in checks if value)
        ratio = positive / len(checks) * 100.0
        return ratio if side == "BULL" else 100.0 - ratio if side == "BEAR" else 50.0

    change = abs(
        _number(
            _first(
                row,
                (
                    "change_pct",
                    "change_percent",
                    "pct_change",
                    "change",
                ),
                0,
            )
        )
    )

    if change:
        return max(35.0, min(100.0, 50.0 + change * 10.0))

    return 50.0 if side == "NEUTRAL" else 60.0


def _normalise_driver(row: dict[str, Any]) -> dict[str, Any]:
    name = _driver_name(row)
    side = _row_side(row)
    score = _row_score(row, side)

    return {
        "name": name,
        "side": side,
        "score": round(score, 2),
        "change_pct": _number(
            _first(
                row,
                (
                    "change_pct",
                    "change_percent",
                    "pct_change",
                    "change",
                ),
                0,
            )
        ),
        "state": str(
            _first(
                row,
                (
                    "driver_state",
                    "state",
                    "status",
                    "verdict",
                ),
                "UNKNOWN",
            )
        ).upper(),
        "raw": row,
    }


def normalise_driver_evidence(
    raw: Any,
    *,
    source: str,
) -> dict[str, Any]:
    rows = _extract_driver_rows(raw)
    normalised = [_normalise_driver(row) for row in rows]

    requested = []
    for name in DEFAULT_DRIVER_NAMES:
        for row in normalised:
            if name in row["name"]:
                requested.append(row)
                break

    selected = requested or normalised

    bull = [row for row in selected if row["side"] == "BULL"]
    bear = [row for row in selected if row["side"] == "BEAR"]
    neutral = [row for row in selected if row["side"] == "NEUTRAL"]

    if len(bull) > len(bear):
        side = "BULL"
    elif len(bear) > len(bull):
        side = "BEAR"
    elif bull or bear:
        side = "NEUTRAL"
    else:
        side = "UNKNOWN"

    directional = bull if side == "BULL" else bear if side == "BEAR" else selected
    score = (
        sum(row["score"] for row in directional) / len(directional)
        if directional
        else 0.0
    )

    total = len(selected)
    aligned = max(len(bull), len(bear))
    agreement_pct = aligned / total * 100.0 if total else 0.0

    if total == 0:
        status = "PARTIAL"
        missing = ["driver_rows"]
    elif side == "UNKNOWN":
        status = "PARTIAL"
        missing = ["driver_side"]
    else:
        status = "CONNECTED"
        missing = []

    if agreement_pct >= 75:
        driver_state = "STRONGLY_ALIGNED"
    elif agreement_pct >= 55:
        driver_state = "ALIGNED"
    elif total:
        driver_state = "MIXED"
    else:
        driver_state = "UNKNOWN"

    leaders = sorted(
        [row for row in selected if row["side"] == side],
        key=lambda row: row["score"],
        reverse=True,
    )

    laggard_side = "BEAR" if side == "BULL" else "BULL"
    laggards = sorted(
        [row for row in selected if row["side"] == laggard_side],
        key=lambda row: row["score"],
        reverse=True,
    )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "status": status,
        "driver_side": side,
        "driver_score": round(score, 2),
        "driver_state": driver_state,
        "agreement_pct": round(agreement_pct, 2),
        "participation": {
            "bull": len(bull),
            "bear": len(bear),
            "neutral": len(neutral),
            "total": total,
        },
        "leaders": [
            {
                "name": row["name"],
                "side": row["side"],
                "score": row["score"],
                "change_pct": row["change_pct"],
                "state": row["state"],
            }
            for row in leaders[:6]
        ],
        "laggards": [
            {
                "name": row["name"],
                "side": row["side"],
                "score": row["score"],
                "change_pct": row["change_pct"],
                "state": row["state"],
            }
            for row in laggards[:6]
        ],
        "drivers": [
            {
                "name": row["name"],
                "side": row["side"],
                "score": row["score"],
                "change_pct": row["change_pct"],
                "state": row["state"],
            }
            for row in selected
        ],
        "missing_fields": missing,
        "note": (
            "Driver Evidence Adapter V1 standardises existing driver output. "
            "It does not invent missing driver evidence."
        ),
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_source(explicit_json: str | None = None) -> tuple[Any, str]:
    if explicit_json:
        path = Path(explicit_json)
        if not path.exists():
            raise FileNotFoundError(f"Driver JSON not found: {path}")
        return _read_json(path), f"json:{path.name}"

    for name in JSON_CANDIDATES:
        path = Path(name)
        if path.exists():
            try:
                raw = _read_json(path)
                rows = _extract_driver_rows(raw)
                if rows:
                    return raw, f"json:{path.name}"
            except Exception:
                continue

    raise FileNotFoundError(
        "No usable driver JSON found. "
        "Checked: " + ", ".join(JSON_CANDIDATES)
    )


def generate_driver_evidence(
    *,
    json_source: str | None = None,
    output_path: str = "driver_evidence_snapshot.json",
) -> dict[str, Any]:
    raw, source = discover_source(json_source)
    result = normalise_driver_evidence(raw, source=source)

    Path(output_path).write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-source")
    parser.add_argument(
        "--output",
        default="driver_evidence_snapshot.json",
    )
    args = parser.parse_args()

    result = generate_driver_evidence(
        json_source=args.json_source,
        output_path=args.output,
    )

    print("DRIVER EVIDENCE SNAPSHOT CREATED")
    print(f"SOURCE       : {result['source']}")
    print(f"STATUS       : {result['status']}")
    print(f"SIDE         : {result['driver_side']}")
    print(f"SCORE        : {result['driver_score']}")
    print(f"STATE        : {result['driver_state']}")
    print(f"PARTICIPATION: {result['participation']}")
    print(f"OUTPUT       : {args.output}")

    if result["missing_fields"]:
        print("MISSING: " + ", ".join(result["missing_fields"]))


if __name__ == "__main__":
    main()
