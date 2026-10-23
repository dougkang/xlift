from datetime import date

import pytest

from ffmodel.adapters.nba_stats.mapping import (
    box_score_row,
    current_season,
    game_status,
    normalize_positions,
    previous_season,
    season_from_season_id,
    season_label,
    season_type_from_game_id,
)


@pytest.mark.parametrize(
    ("gid", "expected"),
    [
        ("0012600009", "preseason"),
        ("0022500585", "regular"),
        ("0032500001", "all_star"),
        ("0042500101", "playoffs"),
        ("0052500101", "play_in"),
        ("0062600001", "cup_final"),
    ],
)
def test_season_type(gid, expected):
    assert season_type_from_game_id(gid) == expected


def test_unknown_prefix():
    with pytest.raises(ValueError):
        season_type_from_game_id("0092500001")


@pytest.mark.parametrize(
    ("status", "postponed", "expected"),
    [
        (3, "N", "final"),
        (1, "N", "scheduled"),
        (2, "N", "scheduled"),
        (1, "Y", "postponed"),
        (3, "Y", "postponed"),
    ],
)
def test_game_status(status, postponed, expected):
    assert game_status(status, postponed) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("G", "G"),
        ("G-F", "G,F"),
        ("F-G", "G,F"),
        ("C-F", "F,C"),
        ("F-C", "F,C"),
        ("", None),
        (None, None),
    ],
)
def test_positions(raw, expected):
    assert normalize_positions(raw) == expected


def test_seasons():
    assert season_from_season_id("22025") == "2025-26"
    assert season_label(2026) == "2026-27"
    assert season_label(2099) == "2099-00"
    assert current_season(date(2026, 10, 23)) == "2026-27"
    assert current_season(date(2027, 3, 1)) == "2026-27"
    assert current_season(date(2026, 8, 1)) == "2025-26"
    assert previous_season("2026-27") == "2025-26"


def test_box_score_row_drops_derived_columns():
    record = {
        "MIN": 29,
        "FGM": 6,
        "FGA": 15,
        "FG_PCT": 0.4,
        "FG3M": 1,
        "FG3A": 6,
        "FTM": 7,
        "FTA": 11,
        "OREB": 1,
        "DREB": 2,
        "REB": 3,
        "AST": 4,
        "STL": 1,
        "BLK": 1,
        "TOV": 1,
        "PF": 2,
        "PTS": 20,
        "PLUS_MINUS": -2,
        "FANTASY_PTS": 34.6,
    }
    row = box_score_row(record, 10, 20, 30)
    assert row["minutes"] == 29.0 and isinstance(row["minutes"], float)
    assert row["pts"] == 20 and row["plus_minus"] == -2
    assert "fg_pct" not in row and "fantasy_pts" not in row
    assert (row["game_id"], row["player_id"], row["team_id"]) == (10, 20, 30)
