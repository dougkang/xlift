import math

import pytest

from ffmodel.tools.impact_analysis.changes import change, tone, transition


@pytest.mark.parametrize(
    ("delta", "better_when", "expected"),
    [
        (2, "higher", "better"),  # W up
        (-2, "higher", "worse"),  # W down
        (1, "lower", "worse"),  # L up, rank number up, TO average up
        (-1, "lower", "better"),  # L down, rank improves
        (3, "neutral", "neutral"),  # T, league average, leader average
        (-3, "neutral", "neutral"),
    ],
)
def test_tone(delta, better_when, expected):
    assert tone(delta, better_when) == expected


def test_opp_average_inverts_category_direction():
    # Opponent's PTS (higher is better for them) going down is better for us.
    assert change(100.0, 110.0, decimals=1, better_when="lower")["tone"] == "better"


@pytest.mark.parametrize(
    ("current", "original", "decimals", "scale"),
    [(10.04, 10.0, 1, 1.0), (0.4504, 0.4500, 3, 1.0), (0.504, 0.500, 0, 100.0), (7, 7, 0, 1.0)],
)
def test_rounds_to_zero_is_none(current, original, decimals, scale):
    assert change(current, original, decimals=decimals, better_when="higher", scale=scale) is None


def test_values_and_scaling():
    assert change(0.61, 0.48, decimals=0, better_when="higher", scale=100) == {
        "delta": 13.0,
        "tone": "better",
    }
    assert change(0.462, 0.450, decimals=3, better_when="higher") == {
        "delta": 0.012,
        "tone": "better",
    }


@pytest.mark.parametrize("bad", [None, math.nan, math.inf])
def test_missing_inputs(bad):
    assert change(bad, 1.0, decimals=1, better_when="higher") is None
    assert change(1.0, bad, decimals=1, better_when="higher") is None


@pytest.mark.parametrize(
    ("orig", "cur", "expected"),
    [
        ("loss", "win", "flip_better"),
        ("win", "loss", "flip_worse"),
        ("loss", "tie", "better"),
        ("tie", "win", "better"),
        ("win", "tie", "worse"),
        ("tie", "loss", "worse"),
        ("win", "win", None),
        ("loss", "loss", None),
        ("tie", "tie", None),
    ],
)
def test_transitions(orig, cur, expected):
    assert transition(orig, cur) == expected


def test_expected_wins_change_is_between_whole_records():  # 010 R4
    from ffmodel.tools.impact_analysis.changes import _expected_wins

    assert _expected_wins({"wins": 5.4}, {"wins": 5.0}) is None  # 5 -> 5
    assert _expected_wins({"wins": 5.5}, {"wins": 5.4}) == {"delta": 1, "tone": "better"}  # 5 -> 6
    assert _expected_wins({"wins": 4.4}, {"wins": 5.0}) == {"delta": -1, "tone": "worse"}
    assert _expected_wins({"wins": 2.5}, {"wins": 1.0}) == {"delta": 2, "tone": "better"}  # half up
