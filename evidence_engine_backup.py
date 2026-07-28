"""
Operation Commander
Module  : Evidence Engine
Purpose : Market, premium aur driver evidence ko CALL/PUT score mein convert karna
"""


CALL = "CALL"
PUT = "PUT"
NEUTRAL = "NEUTRAL"


EVIDENCE_WEIGHTS = {
    "pdc": 10,
    "pdh_pdl": 15,
    "vwap": 15,
    "ema75": 15,
    "opening_range": 20,
    "drivers": 15,
    "premium": 10,
}


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def add_evidence(
    evidence,
    name,
    side,
    weight,
    reason,
):
    evidence.append(
        {
            "name": name,
            "side": side,
            "weight": weight,
            "reason": reason,
        }
    )


def score_market_structure(data):
    """
    Expected fields:
        ltp
        pdc
        pdh
        pdl
        vwap_state
        ema_structure
        or_status
    """

    evidence = []

    ltp = safe_float(data.get("ltp"))
    pdc = safe_float(data.get("pdc"))
    pdh = safe_float(data.get("pdh"))
    pdl = safe_float(data.get("pdl"))

    # PDC
    if pdc > 0:
        if ltp > pdc:
            add_evidence(
                evidence,
                "PDC",
                CALL,
                EVIDENCE_WEIGHTS["pdc"],
                "Price above previous day close",
            )
        elif ltp < pdc:
            add_evidence(
                evidence,
                "PDC",
                PUT,
                EVIDENCE_WEIGHTS["pdc"],
                "Price below previous day close",
            )
        else:
            add_evidence(
                evidence,
                "PDC",
                NEUTRAL,
                0,
                "Price at previous day close",
            )

    # PDH / PDL
    if pdh > 0 and ltp > pdh:
        add_evidence(
            evidence,
            "PDH",
            CALL,
            EVIDENCE_WEIGHTS["pdh_pdl"],
            "Price above previous day high",
        )

    elif pdl > 0 and ltp < pdl:
        add_evidence(
            evidence,
            "PDL",
            PUT,
            EVIDENCE_WEIGHTS["pdh_pdl"],
            "Price below previous day low",
        )

    else:
        add_evidence(
            evidence,
            "PDH_PDL",
            NEUTRAL,
            0,
            "Price inside previous day range",
        )

    # VWAP
    vwap_state = str(
        data.get("vwap_state", "UNKNOWN")
    ).upper()

    if vwap_state == "ABOVE_VWAP":
        add_evidence(
            evidence,
            "VWAP",
            CALL,
            EVIDENCE_WEIGHTS["vwap"],
            "Price above VWAP",
        )

    elif vwap_state == "BELOW_VWAP":
        add_evidence(
            evidence,
            "VWAP",
            PUT,
            EVIDENCE_WEIGHTS["vwap"],
            "Price below VWAP",
        )

    else:
        add_evidence(
            evidence,
            "VWAP",
            NEUTRAL,
            0,
            f"VWAP state {vwap_state}",
        )

    # EMA75
    ema_structure = str(
        data.get("ema_structure", "UNKNOWN")
    ).upper()

    if ema_structure == "ABOVE_BOTH":
        add_evidence(
            evidence,
            "EMA75",
            CALL,
            EVIDENCE_WEIGHTS["ema75"],
            "Price above EMA75 high and low",
        )

    elif ema_structure == "BELOW_BOTH":
        add_evidence(
            evidence,
            "EMA75",
            PUT,
            EVIDENCE_WEIGHTS["ema75"],
            "Price below EMA75 high and low",
        )

    else:
        add_evidence(
            evidence,
            "EMA75",
            NEUTRAL,
            0,
            f"EMA75 structure {ema_structure}",
        )

    # Opening Range
    or_status = str(
        data.get("or_status", "UNKNOWN")
    ).upper()

    if or_status == "ABOVE_ORH":
        add_evidence(
            evidence,
            "OPENING_RANGE",
            CALL,
            EVIDENCE_WEIGHTS["opening_range"],
            "Price above opening range high",
        )

    elif or_status == "BELOW_ORL":
        add_evidence(
            evidence,
            "OPENING_RANGE",
            PUT,
            EVIDENCE_WEIGHTS["opening_range"],
            "Price below opening range low",
        )

    else:
        add_evidence(
            evidence,
            "OPENING_RANGE",
            NEUTRAL,
            0,
            f"Opening range state {or_status}",
        )

    return evidence


def score_single_driver(driver):
    """
    Driver score:
        Above PDC       = 15
        Above PDH       = 20
        Above VWAP      = 20
        Above EMA75     = 20
        Above ORH       = 25

    Bearish side uses opposite conditions.
    """

    if driver.get("error"):
        return {
            "name": driver.get("name", "UNKNOWN"),
            "bull_score": 0,
            "bear_score": 0,
            "maximum_score": 100,
            "state": "ERROR",
            "reasons": [driver["error"]],
        }

    bull_score = 0
    bear_score = 0
    bull_reasons = []
    bear_reasons = []

    if driver.get("above_pdc"):
        bull_score += 15
        bull_reasons.append("Above PDC")

    elif driver.get("below_pdc"):
        bear_score += 15
        bear_reasons.append("Below PDC")

    if driver.get("above_pdh"):
        bull_score += 20
        bull_reasons.append("Above PDH")

    elif driver.get("below_pdl"):
        bear_score += 20
        bear_reasons.append("Below PDL")

    if driver.get("above_vwap"):
        bull_score += 20
        bull_reasons.append("Above VWAP")

    elif driver.get("below_vwap"):
        bear_score += 20
        bear_reasons.append("Below VWAP")

    if driver.get("above_ema75_high"):
        bull_score += 20
        bull_reasons.append("Above EMA75 High")

    elif driver.get("below_ema75_low"):
        bear_score += 20
        bear_reasons.append("Below EMA75 Low")

    if driver.get("above_or_high"):
        bull_score += 25
        bull_reasons.append("Above Opening Range High")

    elif driver.get("below_or_low"):
        bear_score += 25
        bear_reasons.append("Below Opening Range Low")

    if bull_score > bear_score:
        state = "BULLISH"
        reasons = bull_reasons

    elif bear_score > bull_score:
        state = "BEARISH"
        reasons = bear_reasons

    else:
        state = "NEUTRAL"
        reasons = bull_reasons + bear_reasons

    return {
        "name": driver.get("name", "UNKNOWN"),
        "symbol": driver.get("symbol"),
        "ltp": safe_float(driver.get("ltp")),
        "bull_score": bull_score,
        "bear_score": bear_score,
        "maximum_score": 100,
        "state": state,
        "reasons": reasons,
    }


def score_drivers(drivers):
    driver_results = {}

    total_bull = 0
    total_bear = 0
    valid_count = 0

    for name, driver in drivers.items():
        result = score_single_driver(driver)
        driver_results[name] = result

        if result["state"] != "ERROR":
            total_bull += result["bull_score"]
            total_bear += result["bear_score"]
            valid_count += 1

    maximum = valid_count * 100

    bull_percent = (
        round((total_bull / maximum) * 100, 2)
        if maximum
        else 0.0
    )

    bear_percent = (
        round((total_bear / maximum) * 100, 2)
        if maximum
        else 0.0
    )

    if bull_percent >= 60 and bull_percent > bear_percent:
        state = "STRONG_BULLISH"

    elif bull_percent >= 40 and bull_percent > bear_percent:
        state = "BULLISH"

    elif bear_percent >= 60 and bear_percent > bull_percent:
        state = "STRONG_BEARISH"

    elif bear_percent >= 40 and bear_percent > bull_percent:
        state = "BEARISH"

    else:
        state = "MIXED"

    return {
        "state": state,
        "bull_percent": bull_percent,
        "bear_percent": bear_percent,
        "drivers": driver_results,
    }


def score_premium(
    premium_snapshot,
    battle_reference=None,
):
    """
    battle_reference absent hone par premium neutral rahega.

    Reference available hone par locked ATM straddle compare hoga.
    """

    current_straddle = safe_float(
        premium_snapshot.get("atm_straddle")
    )

    if not battle_reference:
        return {
            "side": NEUTRAL,
            "weight": 0,
            "state": "REFERENCE_NOT_LOCKED",
            "current_straddle": current_straddle,
            "reference_straddle": 0.0,
            "change": 0.0,
            "change_pct": 0.0,
        }

    reference_straddle = safe_float(
        battle_reference.get("atm_straddle")
        or battle_reference.get(
            "premium",
            {},
        ).get("atm_straddle")
    )

    if reference_straddle <= 0:
        return {
            "side": NEUTRAL,
            "weight": 0,
            "state": "REFERENCE_UNAVAILABLE",
            "current_straddle": current_straddle,
            "reference_straddle": reference_straddle,
            "change": 0.0,
            "change_pct": 0.0,
        }

    change = current_straddle - reference_straddle
    change_pct = (
        change / reference_straddle
    ) * 100

    if change_pct >= 5:
        state = "STRADDLE_EXPANSION"
        side = NEUTRAL
        weight = EVIDENCE_WEIGHTS["premium"]

    elif change_pct <= -5:
        state = "STRADDLE_DECAY"
        side = NEUTRAL
        weight = EVIDENCE_WEIGHTS["premium"]

    else:
        state = "STRADDLE_TIME_PASS"
        side = NEUTRAL
        weight = 0

    return {
        "side": side,
        "weight": weight,
        "state": state,
        "current_straddle": round(
            current_straddle,
            2,
        ),
        "reference_straddle": round(
            reference_straddle,
            2,
        ),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
    }


def build_evidence_matrix(
    market_data,
    drivers=None,
    premium_snapshot=None,
    battle_reference=None,
):
    evidence = score_market_structure(
        market_data
    )

    driver_summary = None
    premium_summary = None

    if drivers:
        driver_summary = score_drivers(drivers)

        if driver_summary["state"] in {
            "BULLISH",
            "STRONG_BULLISH",
        }:
            add_evidence(
                evidence,
                "DRIVERS",
                CALL,
                EVIDENCE_WEIGHTS["drivers"],
                driver_summary["state"],
            )

        elif driver_summary["state"] in {
            "BEARISH",
            "STRONG_BEARISH",
        }:
            add_evidence(
                evidence,
                "DRIVERS",
                PUT,
                EVIDENCE_WEIGHTS["drivers"],
                driver_summary["state"],
            )

        else:
            add_evidence(
                evidence,
                "DRIVERS",
                NEUTRAL,
                0,
                driver_summary["state"],
            )

    if premium_snapshot:
        premium_summary = score_premium(
            premium_snapshot,
            battle_reference,
        )

        add_evidence(
            evidence,
            "PREMIUM",
            premium_summary["side"],
            premium_summary["weight"],
            premium_summary["state"],
        )

    call_score = sum(
        item["weight"]
        for item in evidence
        if item["side"] == CALL
    )

    put_score = sum(
        item["weight"]
        for item in evidence
        if item["side"] == PUT
    )

    maximum_score = sum(
        EVIDENCE_WEIGHTS.values()
    )

    call_confidence = round(
        (call_score / maximum_score) * 100,
        2,
    )

    put_confidence = round(
        (put_score / maximum_score) * 100,
        2,
    )

    if call_score >= 60 and call_score > put_score:
        verdict = "CALL_BIAS"

    elif put_score >= 60 and put_score > call_score:
        verdict = "PUT_BIAS"

    elif call_score > put_score:
        verdict = "WEAK_CALL_BIAS"

    elif put_score > call_score:
        verdict = "WEAK_PUT_BIAS"

    else:
        verdict = "NO_BIAS"

    return {
        "call_score": call_score,
        "put_score": put_score,
        "maximum_score": maximum_score,
        "call_confidence": call_confidence,
        "put_confidence": put_confidence,
        "verdict": verdict,
        "evidence": evidence,
        "driver_summary": driver_summary,
        "premium_summary": premium_summary,
    }


def print_evidence_matrix(result):
    print("=" * 80)
    print("EVIDENCE MATRIX".center(80))
    print("=" * 80)

    for item in result["evidence"]:
        print(
            f"{item['name']:<20}"
            f"{item['side']:<10}"
            f"{item['weight']:>5}   "
            f"{item['reason']}"
        )

    print("-" * 80)

    print(
        f"CALL SCORE               : "
        f"{result['call_score']} / "
        f"{result['maximum_score']}"
    )
    print(
        f"PUT SCORE                : "
        f"{result['put_score']} / "
        f"{result['maximum_score']}"
    )
    print(
        f"CALL CONFIDENCE          : "
        f"{result['call_confidence']:.2f}%"
    )
    print(
        f"PUT CONFIDENCE           : "
        f"{result['put_confidence']:.2f}%"
    )
    print(
        f"COMMANDER BIAS           : "
        f"{result['verdict']}"
    )

    print("=" * 80)
