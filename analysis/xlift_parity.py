"""Parity checks for 007: the app's xLift and dAB against the analysis notebooks.

Run: cd analysis && uv run python xlift_parity.py

- SC-001: max |xLift app − rankings notebook| over free agents ≤ 0.05, for the league's first
  team. Both run under the window availability (the app's *Last 15*), the only option where the
  notebook's lines and weekly spreads match the app's (research R10).
- SC-005: max |dAB app − availability report| over rostered players ≤ 0.001.
- 009 SC-003: the Player Analysis leaderboard against the notebook, under the same window
  availability: *Your team* for the first team, and *League* (position-neutral) over free agents.
  The app scores a team's open active slot as an empty slot and the notebook doesn't, so where
  teams have one, *League* is judged on the average over the teams without one (research R4).

Exits nonzero on a FAIL.
"""

import importlib.util
import sys
import tempfile
from datetime import date
from pathlib import Path

import numpy as np

import availability as av
from ffmodel.contract.db import get_engine
from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.fragility import dab_values
from ffmodel.tools.impact_analysis.picker import list_players
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from ffmodel.tools.player_analysis.leaderboard import leaderboard
from ffmodel.tools.player_analysis.settings import LeaderboardQuery, PlayerAnalysisSettings

HERE = Path(__file__).resolve().parent
XLIFT_TOL, DAB_TOL = 0.05, 0.001


def notebook_with_window_availability():
    """The rankings notebook with its Availability default set to the window estimate."""
    src = (HERE / "player_rankings_analysis.py").read_text()
    old = """        value="dAB × tag",
        label="Availability","""
    assert src.count(old) == 1, "the notebook's Availability control changed"
    src = src.replace(
        old,
        """        value="Window (current model)",
        label="Availability",""",
    )
    path = Path(tempfile.mkdtemp()) / "rankings_window.py"
    path.write_text(src)
    spec = importlib.util.spec_from_file_location("rankings_window", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.app


def check_xlift(engine, today: date, defs) -> bool:
    snapshot, team_ids = defs["snapshot"], defs["team_ids"]
    team = team_ids[0]
    ti = team_ids.index(team)
    nb = dict(zip(defs["player_ids"], np.nansum(defs["rgp"][ti], axis=1), strict=True))
    fa = {p.player_id for p in defs["free_agents"]}

    cache.clear()
    s = AnalysisSettings(
        league_id=snapshot.settings.league_id,
        team_id=team,
        as_of=today,
        window=82,
        games_per_period=3,
        fragility="last15",
    )
    with engine.connect() as conn:
        rows = list_players(conn, s, free_agents_only=True, limit=200)["players"]
        total = list_players(conn, s, free_agents_only=True, limit=1)["total"]
        offset = 200
        while offset < total:
            rows += list_players(conn, s, free_agents_only=True, limit=200, offset=offset)[
                "players"
            ]
            offset += 200
    app = {r["player_id"]: r["xlift"] for r in rows if r["xlift"] is not None}
    shared = sorted(app.keys() & nb.keys() & fa)
    diffs = np.array([abs(app[p] - nb[p]) for p in shared])
    worst = shared[int(np.argmax(diffs))] if shared else None
    ok = bool(shared) and float(diffs.max()) <= XLIFT_TOL
    print(
        f"SC-001  team {team}: {len(shared)} free agents compared;"
        f" max |xLift app − notebook| = {diffs.max() if shared else float('nan'):.4f}"
        f" (player {worst}) — {'PASS' if ok else 'FAIL'} (≤ {XLIFT_TOL})"
    )
    return ok


def _board(conn, s, **query) -> dict[int, float]:
    q = LeaderboardQuery(pool="free_agents", top=None, min_games=1, **query)
    return {e["player_id"]: e["xlift"] for e in leaderboard(conn, s, q)["entries"]}


def _report(label: str, app: dict, nb: dict, keep, judged: bool = True) -> bool:
    shared = sorted(app.keys() & nb.keys() & keep)
    diffs = np.array([abs(app[p] - nb[p]) for p in shared])
    ok = bool(shared) and float(diffs.max()) <= XLIFT_TOL
    worst = shared[int(np.argmax(diffs))] if shared else None
    print(
        f"{label}: {len(shared)} free agents compared;"
        f" max |leaderboard − notebook| = {diffs.max() if shared else float('nan'):.4f}"
        + (
            f" (player {worst}) — {'PASS' if ok else 'FAIL'} (≤ {XLIFT_TOL})"
            if judged
            else f" (player {worst}) — not judged: open slots are scored differently"
        )
    )
    return ok


def check_leaderboard(engine, today: date, defs) -> bool:
    """009 SC-003: Your team and League against the notebook's leaderboard (research R4)."""
    from ffmodel.core.scenario import from_snapshot

    snapshot, team_ids, rgp = defs["snapshot"], defs["team_ids"], defs["rgp"]
    fa = {p.player_id for p in defs["free_agents"]}
    by_player = dict(zip(defs["player_ids"], range(len(defs["player_ids"])), strict=True))
    league_id = snapshot.settings.league_id

    def settings(team):
        return PlayerAnalysisSettings(
            league_id=league_id, team_id=team, as_of=today, window=82, fragility="last15"
        )

    def nb_for(rows) -> dict[int, float]:
        sums = np.nansum(rows, axis=-1)
        return {p: float(sums[i]) for p, i in by_player.items()}

    cache.clear()
    scenario = from_snapshot(snapshot)
    open_teams = [t for t in team_ids if scenario.open_active_slots(t) > 0]
    closed = [team_ids.index(t) for t in team_ids if t not in open_teams]
    with engine.connect() as conn:
        team = team_ids[0]
        ok = _report(
            f"009     Your team ({team})", _board(conn, settings(team)), nb_for(rgp[0]), fa
        )
        full = _board(conn, settings(team), evaluate_for="league")
        print(f"009     teams with an open active slot: {open_teams or 'none'}")
        if not open_teams:
            return _report("009     League", full, nb_for(np.nanmean(rgp, axis=0)), fa) and ok
        # Informational: the whole league, where the two models differ on open slots.
        _report(
            "009     League, all teams", full, nb_for(np.nanmean(rgp, axis=0)), fa, judged=False
        )
        per_team = [_board(conn, settings(team_ids[ti])) for ti in closed]
        app = {
            p: float(np.mean([b[p] for b in per_team])) for p in fa if all(p in b for b in per_team)
        }
        nb = nb_for(np.nanmean(rgp[closed], axis=0))
        return _report("009     League, teams without an open slot", app, nb, fa) and ok


def check_dab(engine, today: date) -> bool:
    data = av.load(engine, today)
    fit = av.fit(av.backtest(data)).fit
    cut = av.cut_after(today)
    with engine.connect() as conn:
        rostered = [
            r[0] for r in conn.exec_driver_sql("SELECT DISTINCT player_id FROM roster_entry")
        ]
        app = dab_values(conn, rostered, today)
    report = {p: fit.blend(data.counts(p, cut))[0] for p in rostered}
    diffs = np.array([abs(app[p] - report[p]) for p in rostered])
    ok = float(diffs.max()) <= DAB_TOL
    print(
        f"SC-005  {len(rostered)} rostered players: max |dAB app − report| = {diffs.max():.5f}"
        f" — {'PASS' if ok else 'FAIL'} (≤ {DAB_TOL})"
        f"  [report fit: ā={fit.abar:.6f} δ={fit.delta} κ={fit.kappa} κw={fit.kappa_w}"
        f" b1={fit.b1:.6f} b2={fit.b2:.6f}]"
    )
    return ok


if __name__ == "__main__":
    engine = get_engine()
    today = date.today()
    _, defs = notebook_with_window_availability().run()
    results = [
        check_xlift(engine, today, defs),
        check_leaderboard(engine, today, defs),
        check_dab(engine, today),
    ]
    sys.exit(0 if all(results) else 1)
