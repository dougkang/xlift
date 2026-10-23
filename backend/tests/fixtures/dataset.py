"""Deterministic fixture dataset loaded through the data contract (FR-025, tasks.md T014).

Every number the core-read tests assert follows from the explicit schedule below.
"""

from datetime import date, timedelta

from sqlalchemy import text

from ffmodel.contract.names import normalize_name

FIXTURE_TODAY = date(2026, 10, 30)
SOURCE = "fixture"

LAL, ATL, GSW, WAS, DAL = 1, 2, 3, 4, 5
TEAMS = [
    (LAL, "LAL", "Los Angeles", "Lakers"),
    (ATL, "ATL", "Atlanta", "Hawks"),
    (GSW, "GSW", "Golden State", "Warriors"),
    (WAS, "WAS", "Washington", "Wizards"),
    (DAL, "DAL", "Dallas", "Mavericks"),
]

DONCIC, NAW, BUTLER, PORTIS, DYBANTSA, TRADESON = 1, 2, 3, 4, 5, 6
OLD_VET, IGGY, SCHRODER, TWIN_LAL, TWIN_GSW, FRED = 7, 8, 9, 10, 11, 12
PLAYERS = [
    (DONCIC, "Luka Dončić", "Luka", "Dončić", "G,F", LAL, 1),
    (NAW, "Nickeil Alexander-Walker", "Nickeil", "Alexander-Walker", "G", ATL, 1),
    (BUTLER, "Jimmy Butler III", "Jimmy", "Butler III", "F", GSW, 1),
    (PORTIS, "Bobby Portis", "Bobby", "Portis", "F,C", WAS, 1),
    (DYBANTSA, "AJ Dybantsa", "AJ", "Dybantsa", "F", WAS, 1),
    (TRADESON, "Trey Tradeson", "Trey", "Tradeson", "F", ATL, 1),
    (OLD_VET, "Old Vet", "Old", "Vet", "C", None, 0),
    (IGGY, "Iggy Injured", "Iggy", "Injured", "G", GSW, 1),
    (SCHRODER, "Dennis Schröder", "Dennis", "Schröder", "G", DAL, 1),
    (TWIN_LAL, "Marcus Twin", "Marcus", "Twin", "G", LAL, 1),
    (TWIN_GSW, "Marcus Twin", "Marcus", "Twin", "F", GSW, 1),
    (FRED, "Free Agent Fred", "Fred", "Agent", "C", DAL, 1),
]

S2526_START, S2526_END = date(2025, 10, 21), date(2026, 4, 12)
S2627_START, S2627_END = date(2026, 10, 20), date(2027, 4, 11)

# 2025-26: 72 LAL games, k = 0..71, every other day; opponent rotates ATL, GSW, WAS, DAL.
LAL_2526_OPPONENTS = [ATL, GSW, WAS, DAL]


def lal_game_id(k: int) -> int:
    return 1000 + k


def lal_game_date(k: int) -> date:
    return S2526_START + timedelta(days=2 * k)


# 2026-27 finals through 2026-10-29: (id, date, home, away)
G = {
    1: (2001, date(2026, 10, 20), LAL, GSW),
    2: (2002, date(2026, 10, 21), WAS, DAL),
    3: (2003, date(2026, 10, 22), GSW, ATL),
    4: (2004, date(2026, 10, 23), LAL, WAS),
    5: (2005, date(2026, 10, 24), GSW, DAL),
    6: (2006, date(2026, 10, 25), ATL, WAS),
    7: (2007, date(2026, 10, 26), LAL, DAL),
    8: (2008, date(2026, 10, 27), GSW, WAS),
    9: (2009, date(2026, 10, 28), LAL, ATL),
}
# 2026-27 upcoming: (id, date, home, away, status)
S = {
    1: (2101, date(2026, 10, 31), LAL, ATL, "scheduled"),
    2: (2102, date(2026, 11, 1), GSW, DAL, "scheduled"),
    3: (2103, date(2026, 11, 2), GSW, WAS, "postponed"),
    4: (2104, date(2026, 11, 3), LAL, GSW, "scheduled"),
    5: (2105, date(2026, 11, 5), GSW, ATL, "cancelled"),
    6: (2106, date(2026, 11, 6), WAS, LAL, "scheduled"),
    7: (2107, date(2026, 11, 8), GSW, DAL, "scheduled"),
}
# Never counted (FR-012): (id, season, type, date, home, away)
NON_REGULAR = [
    (3001, "2026-27", "preseason", date(2026, 10, 10), LAL, ATL),
    (3002, "2025-26", "play_in", date(2026, 4, 15), LAL, ATL),
    (3003, "2025-26", "playoffs", date(2026, 4, 19), LAL, GSW),
]


def _box(player_id: int, game_id: int, team_id: int) -> dict:
    seed = player_id * 7 + game_id
    fga = 8 + seed % 8
    fgm = fga // 2
    fg3m, fg3a, ftm, fta = 1, 3, 3, 4
    oreb, dreb = 1, 3 + seed % 4
    return {
        "game_id": game_id,
        "player_id": player_id,
        "team_id": team_id,
        "minutes": 30.0,
        "fgm": fgm,
        "fga": fga,
        "fg3m": fg3m,
        "fg3a": fg3a,
        "ftm": ftm,
        "fta": fta,
        "oreb": oreb,
        "dreb": dreb,
        "reb": oreb + dreb,
        "ast": 2 + seed % 5,
        "stl": seed % 3,
        "blk": seed % 2,
        "tov": 2,
        "pf": 2,
        "pts": 2 * (fgm - fg3m) + 3 * fg3m + ftm,
        "plus_minus": seed % 11 - 5,
    }


def _insert(conn, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    cols = list(rows[0])
    conn.execute(
        text(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})"
        ),
        rows,
    )


def _game(game_id, season, season_type, day, home, away, status="final") -> dict:
    return {
        "game_id": game_id,
        "season_id": season,
        "season_type": season_type,
        "game_date": day.isoformat(),
        "home_team_id": home,
        "away_team_id": away,
        "status": status,
    }


def load_fixture(conn) -> None:
    _insert(
        conn,
        "season",
        [
            {
                "season_id": "2025-26",
                "start_date": S2526_START.isoformat(),
                "end_date": S2526_END.isoformat(),
            },
            {
                "season_id": "2026-27",
                "start_date": S2627_START.isoformat(),
                "end_date": S2627_END.isoformat(),
            },
        ],
    )
    _insert(
        conn,
        "nba_team",
        [{"team_id": t, "abbreviation": a, "city": c, "name": n} for t, a, c, n in TEAMS],
    )
    _insert(
        conn,
        "nba_team_external_id",
        [{"source": SOURCE, "external_id": a, "team_id": t} for t, a, _, _ in TEAMS],
    )
    _insert(
        conn,
        "player",
        [
            {
                "player_id": pid,
                "full_name": full,
                "first_name": first,
                "last_name": last,
                "search_name": normalize_name(full),
                "positions": pos,
                "current_team_id": team,
                "is_active": active,
            }
            for pid, full, first, last, pos, team, active in PLAYERS
        ],
    )
    _insert(
        conn,
        "player_external_id",
        [
            {"source": SOURCE, "external_id": str(p[0]), "player_id": p[0], "match_method": "exact"}
            for p in PLAYERS
        ],
    )

    games, boxes = [], []

    # 2025-26 LAL schedule.
    for k in range(72):
        opp = LAL_2526_OPPONENTS[k % 4]
        home, away = (LAL, opp) if k % 2 == 0 else (opp, LAL)
        gid = lal_game_id(k)
        games.append(_game(gid, "2025-26", "regular", lal_game_date(k), home, away))
        if k not in (10, 11):
            boxes.append(_box(DONCIC, gid, LAL))
        if k <= 29:
            boxes.append(_box(OLD_VET, gid, LAL))
        if opp == DAL and k <= 51:
            boxes.append(_box(TRADESON, gid, DAL))
        if opp == ATL and k >= 56:
            boxes.append(_box(TRADESON, gid, ATL))

    # 2026-27 finals and upcoming games.
    for gid, day, home, away in G.values():
        games.append(_game(gid, "2026-27", "regular", day, home, away))
    for gid, day, home, away, status in S.values():
        games.append(_game(gid, "2026-27", "regular", day, home, away, status))
    for gid, season, stype, day, home, away in NON_REGULAR:
        games.append(_game(gid, season, stype, day, home, away))
        boxes.append(_box(DONCIC, gid, LAL))

    appearances = {
        DONCIC: (LAL, [1, 4, 7, 9]),
        DYBANTSA: (WAS, [2, 4, 6]),
        IGGY: (GSW, [3, 8]),
        NAW: (ATL, [3, 6]),
        BUTLER: (GSW, [1, 3, 5]),
        PORTIS: (WAS, [2, 4]),
        SCHRODER: (DAL, [2, 5, 7]),
        TWIN_LAL: (LAL, [1, 4]),
        TWIN_GSW: (GSW, [5, 8]),
        FRED: (DAL, [5, 7]),
    }
    for pid, (team, game_numbers) in appearances.items():
        for n in game_numbers:
            boxes.append(_box(pid, G[n][0], team))

    _insert(conn, "game", games)
    _insert(conn, "player_game", boxes)

    stints = [
        (DONCIC, LAL, S2526_START, S2526_END),
        (OLD_VET, LAL, S2526_START, date(2025, 12, 18)),
        (TRADESON, DAL, S2526_START, date(2026, 2, 9)),
        (TRADESON, ATL, date(2026, 2, 10), None),
    ]
    for pid, _, _, _, _, team, active in PLAYERS:
        if active and pid != TRADESON:
            stints.append((pid, team, S2627_START, None))
    _insert(
        conn,
        "player_team_stint",
        [
            {
                "player_id": p,
                "team_id": t,
                "start_date": s.isoformat(),
                "end_date": e.isoformat() if e else None,
            }
            for p, t, s, e in stints
        ],
    )

    _insert(
        conn,
        "fantasy_league",
        [
            {
                "league_id": 1,
                "league_key": "fixture-league",
                "name": "Fixture League",
                "season_id": "2026-27",
                "scoring_format_id": "9cat_h2h",
                "active_roster_capacity": 3,
            }
        ],
    )
    _insert(
        conn,
        "manager",
        [
            {"manager_id": 1, "league_id": 1, "display_name": "Ann"},
            {"manager_id": 2, "league_id": 1, "display_name": "Bo"},
        ],
    )
    _insert(
        conn,
        "fantasy_team",
        [
            {
                "fantasy_team_id": 1,
                "league_id": 1,
                "source_team_key": "t.01",
                "name": "Alpha",
                "manager_id": 1,
            },
            {
                "fantasy_team_id": 2,
                "league_id": 1,
                "source_team_key": "t.02",
                "name": "Beta",
                "manager_id": 2,
            },
        ],
    )
    roster = [
        (DONCIC, 1, "active"),
        (BUTLER, 1, "active"),
        (DYBANTSA, 1, "active"),
        (IGGY, 1, "reserve"),
        (NAW, 2, "active"),
        (SCHRODER, 2, "active"),
    ]
    _insert(
        conn,
        "roster_entry",
        [
            {
                "league_id": 1,
                "player_id": p,
                "fantasy_team_id": t,
                "slot": s,
                "source_positions": None,
            }
            for p, t, s in roster
        ],
    )
    status = {IGGY: "IL", BUTLER: "Q"}
    _insert(
        conn,
        "player_status",
        [
            {
                "player_id": p,
                "source": SOURCE,
                "as_of": "2026-10-29",
                "status": status.get(p, "healthy"),
            }
            for p, _, _ in roster
        ],
    )
