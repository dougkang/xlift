"""SC-006 / SC-007: every core read works from the contract alone, with no network."""

import socket
import subprocess
import sys
from datetime import date

import pytest

import ffmodel.core.data as data
from tests.fixtures import dataset as fx


def test_network_is_blocked():
    with pytest.raises(RuntimeError, match="network disabled"):
        socket.create_connection(("example.com", 80), timeout=1)


def test_every_public_read_works_offline(fixture_engine):
    readers = sorted(n for n in data.__all__ if n[0].islower())
    assert readers == [
        "count_team_games",
        "get_availability",
        "get_free_agents",
        "get_last_n_games",
        "get_league",
        "get_player",
        "get_player_history",
        "list_leagues",
        "search_players",
    ]
    with fixture_engine.connect() as conn:
        # SC-007: each Impact Analysis input maps to the read that answers it.
        window = data.get_last_n_games(conn, fx.DONCIC, 15, as_of=fx.FIXTURE_TODAY)
        assert window.found == 15  # last-X-game window
        assert (
            data.count_team_games(
                conn, fx.IGGY, date(2026, 10, 31), date(2026, 11, 8), statuses=("scheduled",)
            )
            == 3
        )  # games in a date range
        assert (
            data.get_availability(
                conn, fx.IGGY, date(2026, 10, 20), date(2026, 10, 29)
            ).games_missed
            == 2
        )  # missed games
        league = data.list_leagues(conn)[0]
        snap = data.get_league(conn, league.league_id)  # rosters and all league teams
        assert len(snap.teams) == 2 and all(t.roster for t in snap.teams)
        assert data.get_free_agents(conn, league.league_id)  # free agents
        statuses = {r.status for t in snap.teams for r in t.roster}
        assert {"IL", "Q"} <= statuses  # current status
        assert data.search_players(conn, "doncic")  # player lookup
        assert data.get_player(conn, fx.DONCIC)
        assert data.get_player_history(conn, fx.DONCIC)


def test_core_does_not_import_nba_api():
    code = "import sys, ffmodel.core.data; assert 'nba_api' not in sys.modules"
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0
