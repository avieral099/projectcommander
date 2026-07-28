from premium_engine import (
    build_required_ladder,
    calculate_straddle_map,
    infer_strike_step,
)


def test_ladder():
    ladder = build_required_ladder(
        atm_strike=23750,
        strike_step=50,
    )

    assert len(ladder) == 14
    assert ladder["ITM3_CE"][0] == 23600
    assert ladder["OTM3_CE"][0] == 23900
    assert ladder["ITM3_PE"][0] == 23900
    assert ladder["OTM3_PE"][0] == 23600


def test_step():
    rows = []

    for strike in (
        23600,
        23650,
        23700,
        23750,
        23800,
        23850,
        23900,
    ):
        rows.append(
            {
                "strike_price": strike,
                "option_type": "CE",
            }
        )
        rows.append(
            {
                "strike_price": strike,
                "option_type": "PE",
            }
        )

    assert infer_strike_step(
        rows,
        23750,
    ) == 50


def test_straddles():
    contracts = {
        "ATM_CE": {
            "strike": 23750,
            "option_type": "CE",
            "ltp": 152.10,
            "oi": 100,
            "volume": 200,
            "symbol": "CE",
        },
        "ATM_PE": {
            "strike": 23750,
            "option_type": "PE",
            "ltp": 81.85,
            "oi": 150,
            "volume": 250,
            "symbol": "PE",
        },
    }

    result = calculate_straddle_map(
        contracts
    )

    assert result[23750][
        "straddle"
    ] == 233.95

    assert result[23750][
        "combined_oi"
    ] == 250


if __name__ == "__main__":
    test_ladder()
    test_step()
    test_straddles()

    print(
        "ALL PREMIUM ENGINE ATM ±3 TESTS PASSED"
    )
