"""Was ESPN's served 2025-26 projection set revised with the season's results? (ccsv-rumble #33)

A set that had seen the results would sit close to the actual averages, would know who got hurt,
and would track a player's late games at least as well as their early ones. Run from analysis/:

    uv run python espn_leak_check.py output/espn_2026.json output/espn_2025.json

The two files are ESPN's player lists for those seasons, fetched as in weekly_backtest.fetch_espn.
"""

import json
import sys
from pathlib import Path

import numpy as np
from ffmodel.contract.db import get_engine

from weekly_backtest import norm_name

GP, PTS = "42", "0"
MIN_GAMES = 20


def lines(path: str, stat_id: str) -> dict[str, tuple[str, float, float]]:
    """Name → (display name, games, points per game) for one of a player's stat sets."""
    out = {}
    for p in json.loads(Path(path).read_text()):
        s = next((s for s in p.get("stats", []) if s["id"] == stat_id), None)
        if s and s.get("stats", {}).get(GP):
            games = s["stats"][GP]
            out[norm_name(p["fullName"])] = (p["fullName"], games, s["stats"].get(PTS, 0) / games)
    return out


def main(season_file: str, prior_file: str):
    proj = lines(season_file, "102026")
    actual = lines(season_file, "002026")
    last = lines(prior_file, "002025")
    names = [
        n for n in proj
        if n in actual and n in last and min(actual[n][1], last[n][1]) >= MIN_GAMES
    ]  # fmt: skip
    p, a, l = (np.array([d[n][2] for n in names]) for d in (proj, actual, last))
    games_p, games_a = (np.array([d[n][1] for n in names]) for d in (proj, actual))
    print(f"{len(names)} players with a projection and {MIN_GAMES}+ games in both seasons")
    print(f"points/game MAE: projection {np.abs(p - a).mean():.2f}, "
          f"last season {np.abs(l - a).mean():.2f}")  # fmt: skip
    print(f"corr(projection - last season, actual - last season): "
          f"{np.corrcoef(p - l, a - l)[0, 1]:.2f}")  # fmt: skip
    print(f"games: corr {np.corrcoef(games_p, games_a)[0, 1]:.2f}, "
          f"mean projected {games_p.mean():.1f}, mean actual {games_a.mean():.1f}")  # fmt: skip

    with get_engine().connect() as conn:
        rows = conn.exec_driver_sql(
            """SELECT p.full_name, pg.pts FROM player_game pg JOIN game g USING (game_id)
               JOIN player p USING (player_id)
               WHERE g.season_id = '2025-26' AND g.season_type = 'regular'
               ORDER BY g.game_date"""
        ).all()
    games = {}
    for name, pts in rows:
        games.setdefault(norm_name(name), []).append(pts)
    keep = [i for i, n in enumerate(names) if len(games.get(n, ())) >= 30]
    thirds = np.array(
        [[part.mean() for part in np.array_split(np.array(games[names[i]], float), 3)] for i in keep]
    )
    for j, label in enumerate(("first", "middle", "last")):
        corr = np.corrcoef(p[keep] - l[keep], thirds[:, j] - l[keep])[0, 1]
        print(f"corr with the {label} third of the player's games: {corr:.2f}")

    print("\nMost games missed against the projection:")
    for n in sorted(names, key=lambda n: actual[n][1] - proj[n][1])[:8]:
        print(f"  {proj[n][0]}: projected {proj[n][1]:.0f}, played {actual[n][1]:.0f}")
    print("\nBiggest jumps in scoring (last season, projected, actual):")
    for n in sorted(names, key=lambda n: last[n][2] - actual[n][2])[:8]:
        print(f"  {proj[n][0]}: {last[n][2]:.1f}, {proj[n][2]:.1f}, {actual[n][2]:.1f}")
    print("\nTop scorers with no projection at all (points/game, games):")
    unprojected = [n for n in actual if n not in proj and actual[n][1] >= MIN_GAMES]
    for n in sorted(unprojected, key=lambda n: -actual[n][2])[:8]:
        print(f"  {actual[n][0]}: {actual[n][2]:.1f}, {actual[n][1]:.0f}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
