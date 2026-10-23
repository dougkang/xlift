"""Fixture for Impact Analysis tool and API tests (002 tasks.md T019).

Independent of tests/fixtures/dataset.py. Every number the tool tests rely on follows from the
explicit schedule and strengths below.
"""

import math
from datetime import date, timedelta

from sqlalchemy import text

from ffmodel.contract.names import normalize_name

IMPACT_TODAY = date(2026, 11, 18)  # Wednesday; fantasy week Mon 11-16 – Sun 11-22
WEEK = (date(2026, 11, 16), date(2026, 11, 22))
SEASON = "2026-27"
SEASON_START, SEASON_END = date(2026, 10, 20), date(2027, 4, 11)
LAST_FINAL = date(2026, 11, 17)

BOS, MIA, NYK, CHI = 1, 2, 3, 4
TEAMS = [
    (BOS, "BOS", "Boston", "Celtics"),
    (MIA, "MIA", "Miami", "Heat"),
    (NYK, "NYK", "New York", "Knicks"),
    (CHI, "CHI", "Chicago", "Bulls"),
]

(
    ALPHA_1,
    ALPHA_2,
    ALPHA_3,
    BETA_1,
    BETA_2,
    BETA_3,
    GAMMA_1,
    GAMMA_2,
    GAMMA_HURT,
    DELTA_1,
    DELTA_2,
    DELTA_3,
    STEADY,
    BUSY,
    ROOKIE,
    BENCH,
) = range(1, 17)

# id: (name, nba team, strength)
PLAYERS = {
    ALPHA_1: ("Alpha One", BOS, 1.5),
    ALPHA_2: ("Alpha Two", NYK, 1.5),
    ALPHA_3: ("Alpha Three", CHI, 1.5),
    BETA_1: ("Beta One", MIA, 1.0),
    BETA_2: ("Beta Two", BOS, 1.0),
    BETA_3: ("Beta Three", NYK, 1.0),
    GAMMA_1: ("Gamma One", CHI, 1.0),
    GAMMA_2: ("Gamma Two", MIA, 1.0),
    GAMMA_HURT: ("Gamma Hurt", NYK, 2.0),
    DELTA_1: ("Delta One", BOS, 0.6),
    DELTA_2: ("Delta Two", MIA, 0.6),
    DELTA_3: ("Delta Three", CHI, 0.6),
    STEADY: ("Steady Streamer", MIA, 1.0),
    BUSY: ("Busy Streamer", BOS, 0.9),
    ROOKIE: ("Rookie Ray", CHI, 1.0),
    BENCH: ("Bench Ben", NYK, 0.3),
}
# league team id: (key, name, manager, [(player, slot)])
FANTASY = {
    1: ("t.A", "Alphas", "Ann", [(ALPHA_1, "active"), (ALPHA_2, "active"), (ALPHA_3, "active")]),
    2: ("t.B", "Betas", "Bo", [(BETA_1, "active"), (BETA_2, "active"), (BETA_3, "active")]),
    3: ("t.C", "Gammas", "Cy", [(GAMMA_1, "active"), (GAMMA_2, "active"), (GAMMA_HURT, "reserve")]),
    4: ("t.D", "Deltas", "Di", [(DELTA_1, "active"), (DELTA_2, "active"), (DELTA_3, "active")]),
}
STATUS = {GAMMA_HURT: "IL", ROOKIE: "Q"}

PAIRINGS = [((BOS, MIA), (NYK, CHI)), ((BOS, NYK), (MIA, CHI)), ((BOS, CHI), (MIA, NYK))]
SCHEDULED = [
    (date(2026, 11, 18), BOS, CHI, "scheduled"),
    (date(2026, 11, 19), BOS, MIA, "scheduled"),
    (date(2026, 11, 20), BOS, NYK, "scheduled"),
    (date(2026, 11, 21), BOS, CHI, "scheduled"),
    (date(2026, 11, 22), NYK, CHI, "scheduled"),
    (date(2026, 11, 21), MIA, NYK, "postponed"),
]
GAMES_REMAINING = {BOS: 4, CHI: 3, NYK: 2, MIA: 1}

BASE = {
    "fga": 15,
    "fgm": 7,
    "fg3a": 6,
    "fg3m": 2,
    "fta": 5,
    "ftm": 4,
    "oreb": 1,
    "dreb": 5,
    "ast": 5,
    "stl": 1,
    "blk": 1,
    "tov": 2,
    "pf": 2,
}


def box(player_id: int, game_index: int, game_id: int, team_id: int, strength: float) -> dict:
    wobble = 1 + 0.25 * math.sin(1.7 * game_index + player_id)
    v = {k: round(b * strength * wobble) for k, b in BASE.items()}
    v["fgm"] = min(v["fgm"], v["fga"])
    v["fg3m"] = min(v["fg3m"], v["fgm"])
    v["fg3a"] = max(min(v["fg3a"], v["fga"]), v["fg3m"])
    v["ftm"] = min(v["ftm"], v["fta"])
    v["reb"] = v["oreb"] + v["dreb"]
    v["pts"] = 2 * v["fgm"] + v["fg3m"] + v["ftm"]
    return {
        "game_id": game_id,
        "player_id": player_id,
        "team_id": team_id,
        "minutes": 30.0,
        "plus_minus": 0,
        **v,
    }


def _insert(conn, table: str, rows: list[dict]) -> None:
    cols = list(rows[0])
    conn.execute(
        text(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"
        ),
        rows,
    )


def load_impact_fixture(conn) -> None:
    _insert(
        conn,
        "season",
        [
            {
                "season_id": SEASON,
                "start_date": SEASON_START.isoformat(),
                "end_date": SEASON_END.isoformat(),
            }
        ],
    )
    _insert(
        conn,
        "nba_team",
        [{"team_id": t, "abbreviation": a, "city": c, "name": n} for t, a, c, n in TEAMS],
    )
    _insert(
        conn,
        "player",
        [
            {
                "player_id": pid,
                "full_name": name,
                "first_name": name.split()[0],
                "last_name": name.split()[-1],
                "search_name": normalize_name(name),
                "positions": "G",
                "current_team_id": team,
                "is_active": 1,
            }
            for pid, (name, team, _) in PLAYERS.items()
        ],
    )

    games, boxes = [], []
    game_id = 0
    team_game_index: dict[int, int] = dict.fromkeys(PAIRINGS[0][0] + PAIRINGS[0][1], 0)
    day = SEASON_START
    d = 0
    while day <= LAST_FINAL:
        for home, away in PAIRINGS[d % 3]:
            game_id += 1
            games.append(
                {
                    "game_id": game_id,
                    "season_id": SEASON,
                    "season_type": "regular",
                    "game_date": day.isoformat(),
                    "home_team_id": home,
                    "away_team_id": away,
                    "status": "final",
                }
            )
            for team in (home, away):
                team_game_index[team] += 1
                for pid, (_, pteam, strength) in PLAYERS.items():
                    if pteam != team:
                        continue
                    if pid == ROOKIE and day < LAST_FINAL - timedelta(days=1):
                        continue  # Rookie Ray: only the last two finals
                    boxes.append(box(pid, team_game_index[team], game_id, team, strength))
        day += timedelta(days=1)
        d += 1
    for day, home, away, status in SCHEDULED:
        game_id += 1
        games.append(
            {
                "game_id": game_id,
                "season_id": SEASON,
                "season_type": "regular",
                "game_date": day.isoformat(),
                "home_team_id": home,
                "away_team_id": away,
                "status": status,
            }
        )
    _insert(conn, "game", games)
    _insert(conn, "player_game", boxes)
    _insert(
        conn,
        "player_team_stint",
        [
            {
                "player_id": pid,
                "team_id": team,
                "start_date": SEASON_START.isoformat(),
                "end_date": None,
            }
            for pid, (_, team, _) in PLAYERS.items()
        ],
    )

    _insert(
        conn,
        "fantasy_league",
        [
            {
                "league_id": 1,
                "league_key": "impact-league",
                "name": "Impact League",
                "season_id": SEASON,
                "scoring_format_id": "9cat_h2h",
                "active_roster_capacity": 3,
            }
        ],
    )
    _insert(
        conn,
        "manager",
        [
            {"manager_id": tid, "league_id": 1, "display_name": mgr}
            for tid, (_, _, mgr, _) in FANTASY.items()
        ],
    )
    _insert(
        conn,
        "fantasy_team",
        [
            {
                "fantasy_team_id": tid,
                "league_id": 1,
                "source_team_key": key,
                "name": name,
                "manager_id": tid,
            }
            for tid, (key, name, _, _) in FANTASY.items()
        ],
    )
    _insert(
        conn,
        "roster_entry",
        [
            {
                "league_id": 1,
                "player_id": pid,
                "fantasy_team_id": tid,
                "slot": slot,
                "source_positions": None,
            }
            for tid, (_, _, _, spots) in FANTASY.items()
            for pid, slot in spots
        ],
    )
    _insert(
        conn,
        "player_status",
        [
            {
                "player_id": pid,
                "source": "yahoo",
                "as_of": IMPACT_TODAY.isoformat(),
                "status": STATUS.get(pid, "healthy"),
            }
            for pid in PLAYERS
        ],
    )
    _insert(
        conn,
        "load_run",
        [
            {
                "source": "nba_stats",
                "scope": "{}",
                "started_at": "2026-11-18T07:59:00+00:00",
                "finished_at": "2026-11-18T08:00:00+00:00",
                "outcome": "succeeded",
                "rows_inserted": 0,
                "rows_updated": 0,
            }
        ],
    )
