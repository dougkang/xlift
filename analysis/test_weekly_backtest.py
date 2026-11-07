"""Tiny-fixture tests for weekly_backtest. Run from analysis/: uv run --with pytest pytest"""

from datetime import date

import numpy as np

import weekly_backtest as wb


def _line(**stats):
    return np.array([float(stats.get(s, 0)) for s in wb.LINE])


def test_cutoffs_are_mondays_through_the_last_week():
    days = wb.cutoffs()
    assert days[0] == date(2025, 10, 27) and days[-1] == date(2026, 4, 6)
    assert all(d.weekday() == 0 for d in days)


def test_window_drops_the_all_star_week_and_past_the_season():
    assert wb.window(date(2026, 2, 2), "week+1") == (date(2026, 2, 2), date(2026, 2, 8))
    assert wb.window(date(2026, 2, 9), "week+1") is not None
    assert wb.window(date(2026, 2, 16), "week+1") is None
    assert wb.window(date(2026, 2, 9), "week+2") is None
    assert wb.window(date(2026, 2, 9), "weeks+1-2") is None
    assert wb.window(date(2026, 2, 16), "week+2") == (date(2026, 2, 23), date(2026, 3, 1))
    assert wb.window(date(2026, 4, 6), "week+1") is not None
    assert wb.window(date(2026, 4, 6), "week+2") is None


def test_missed_last_week_needs_two_club_games_all_missed():
    club = np.array(["2025-11-01", "2025-11-05", "2025-11-07"])
    cut, ago = "2025-11-10", "2025-11-03"
    assert wb.missed_last_week(np.array(["2025-11-01"]), club, cut, ago)
    assert not wb.missed_last_week(np.array(["2025-11-05"]), club, cut, ago)
    one = np.array(["2025-11-01", "2025-11-05"])
    assert not wb.missed_last_week(np.array(["2025-11-01"]), one, cut, ago)


def test_spearman_is_rank_only_and_nan_when_constant():
    assert wb.spearman(np.array([1.0, 2, 3, 4]), np.array([1.0, 8, 27, 64])) == 1
    assert wb.spearman(np.array([1.0, 2, 3, 4]), np.array([4.0, 3, 2, 1])) == -1
    assert np.isnan(wb.spearman(np.array([1.0, 1, 1]), np.array([1.0, 2, 3])))


def test_categories_score_percentages_as_impact():
    line = _line(pts=10, fgm=5, fga=10, ftm=4, fta=4)
    cats = wb.categories(line, fg_rate=0.4, ft_rate=0.75)
    assert cats[wb.CATS.index("pts")] == 10
    assert cats[wb.CATS.index("fg_impact")] == 5 - 0.4 * 10
    assert cats[wb.CATS.index("ft_impact")] == 4 - 0.75 * 4


def test_value_counts_turnovers_against():
    sd = np.ones(len(wb.CATS))
    cats = np.zeros(len(wb.CATS))
    cats[wb.CATS.index("tov")] = 2
    cats[wb.CATS.index("pts")] = 3
    assert wb.value(cats, sd) == 1


def test_score_reports_error_rank_and_games():
    act = np.zeros((4, len(wb.CATS)))
    act[:, 0] = [10, 20, 30, 40]
    act[:, 1:] = np.arange(1, 5)[:, None]
    pred = act.copy()
    pred[:, 0] += 2
    rows = wb.score(
        date(2025, 11, 3), "week+1", 180, "all", "espn", pred, act,
        np.array([3.0, 3, 3, 3]), np.array([2.0, 3, 3, 3]), pred[:3], act[:3],
    )  # fmt: skip
    by = {r["cat"]: r for r in rows}
    assert by["pts"]["mae"] == 2 and by["pts"]["bias"] == 2 and by["pts"]["rank"] == 1
    assert by["reb"]["mae"] == 0
    assert by["games"]["mae"] == 0.25 and by["games"]["bias"] == 0.25
    assert by["pts"]["rate_mae"] == 2


def test_espn_lines_reads_the_projected_set_per_game():
    players = [
        {
            "fullName": "Nikola Jokić",
            "stats": [
                {"id": "002026", "stats": {"42": 10, "0": 999}},
                {"id": "102026", "stats": {"42": 50, "0": 1500, "17": 100}},
            ],
        },
        {"fullName": "No Line", "stats": [{"id": "002026", "stats": {"42": 10}}]},
        {"fullName": "No Games", "stats": [{"id": "102026", "stats": {"0": 4}}]},
    ]
    lines = wb.espn_lines(players)
    assert list(lines) == ["nikola jokic"]
    assert lines["nikola jokic"][wb.L["pts"]] == 30
    assert lines["nikola jokic"][wb.L["fg3m"]] == 2


def test_norm_name_strips_suffixes_and_applies_aliases():
    assert wb.norm_name("Jaren Jackson Jr.") == "jaren jackson"
    assert wb.norm_name("Gary Payton II") == "gary payton"
    assert wb.norm_name("Nicolas Claxton") == "nic claxton"
    assert wb.norm_name("Luka Dončić") == "luka doncic"
