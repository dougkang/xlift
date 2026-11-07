"""Is a player's next game or week just another draw from their previous games? (ccsv-rumble #33)

The null hypothesis is that a player's games are exchangeable for a given stat: the next game, or
the next week's games, could have been any of the games so far. That gives exact tests with no
assumed distribution:

- **next game**: the game's rank among the previous games is uniform;
- **week**: the week's total is an ordinary draw from all ways of splitting these games into a
  prior set and a week of the same length (a permutation test). The games played are held fixed,
  so this tests production when playing. A second version pads missed club games with zeros.

Each test gives `u`, the outcome's position in that null distribution, with ties split at random
so that `u` is exactly uniform under the null. So 5% of tests reject at the 5% level by design,
and the question is how far past 5% they go. FG% and FT% are tested as makes and attempts.

The model's prediction is tested against the same distribution: is the predicted per-game line
for the week outside what `g` of the player's previous games would average by chance, and does
the outcome follow when it is?

Needs 2024-25 as well, so use the database copy described in weekly_backtest.py:

    (cd analysis && uv run python distribution_test.py)
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl
from ffmodel.contract.db import get_engine
from ffmodel.core.model import build_projections
from ffmodel.core.scoring import get_format
from scipy.stats import kstest

import weekly_backtest as wb

SEASON, PRIOR_SEASON = wb.SEASON, wb.PRIOR_SEASON
STATS = ("minutes", "pts", "reb", "ast", "stl", "blk", "fg3m", "fg3a", "tov",
         "fgm", "fga", "ftm", "fta")  # fmt: skip
TESTED = STATS[1:]  # minutes is shown as a control
S = {s: i for i, s in enumerate(STATS)}
MIN_PRIOR = 10
ROTATION_MINUTES = 20
ACTIVE_DAYS = 14  # a week is tested only for players who played this recently
ALPHA = 0.05
PERMUTATIONS = 999
WINDOWS = ("season", "last15", "last30", "two_seasons")
SEED = 33
HERE = Path(__file__).parent


def rank_u(prior: np.ndarray, x: float, tie: float) -> float:
    """The position of `x` among `prior`, exactly uniform when all are exchangeable."""
    below = int((prior < x).sum())
    equal = int((prior == x).sum())
    return (below + tie * (equal + 1)) / (len(prior) + 1)


def permutation_u(
    prior: np.ndarray, actual: np.ndarray, rng: np.random.Generator, permutations: int = PERMUTATIONS
) -> np.ndarray:
    """Per column, the position of the `actual` games' total among random equal-sized subsets of
    all the games. `prior` and `actual` are (games, stats)."""
    pool = np.vstack([prior, actual])
    g = len(actual)
    subsets = rng.random((permutations, len(pool))).argsort(axis=1)[:, :g]
    totals = pool[subsets].sum(axis=1)
    observed = actual.sum(axis=0)
    below = (totals < observed).sum(axis=0)
    equal = (totals == observed).sum(axis=0)
    tie = rng.random(pool.shape[1])
    return (below + tie * (equal + 1)) / (permutations + 1)


def p_value(u):
    return 2 * np.minimum(u, 1 - u)


def real_share(p: np.ndarray, cut: float = 0.5) -> float:
    """Storey's estimate of the share of tests where the null is actually false."""
    return float(max(0.0, 1 - (p > cut).mean() / (1 - cut)))


def bh_reject(p: np.ndarray, q: float = 0.05) -> np.ndarray:
    """Benjamini-Hochberg: which tests survive a false-discovery rate of `q`."""
    order = np.argsort(p)
    passing = p[order] <= q * np.arange(1, len(p) + 1) / len(p)
    keep = np.zeros(len(p), bool)
    if passing.any():
        keep[order[: int(np.nonzero(passing)[0].max()) + 1]] = True
    return keep


def tier(x: float, edges: tuple, labels: tuple) -> str:
    return labels[int(np.searchsorted(edges, x, side="right"))]


def minutes_tier(x):
    return tier(x, (15, 25, 32), ("under 15 min", "15-25 min", "25-32 min", "32+ min"))


def scoring_tier(x):
    return tier(x, (10, 15, 20, 25), ("under 10 pts", "10-15 pts", "15-20 pts", "20-25 pts", "25+ pts"))


def games_tier(n):
    return tier(n, (20, 40), ("10-19 prior games", "20-39 prior games", "40+ prior games"))


def period_of(d: str) -> str:
    if d < "2025-12-01":
        return "Oct-Nov"
    return "final 4 weeks" if d >= wb.FINAL_START.isoformat() else "Dec-mid Mar"


@dataclass
class Player:
    dates: np.ndarray
    lines: np.ndarray
    teams: np.ndarray
    homes: np.ndarray
    first_season: int  # index of the first 2025-26 game


def load(conn):
    cols = ", ".join(f"pg.{s}" for s in STATS)
    rows = conn.exec_driver_sql(
        f"""SELECT pg.player_id, g.game_date, g.season_id, pg.team_id, g.home_team_id, {cols}
            FROM player_game pg JOIN game g USING (game_id)
            WHERE g.season_type = 'regular' AND g.status = 'final' AND g.season_id IN (?, ?)
            ORDER BY pg.player_id, g.game_date""",
        (PRIOR_SEASON, SEASON),
    ).all()
    by = defaultdict(list)
    for r in rows:
        by[r[0]].append(r)
    players = {}
    for pid, rs in by.items():
        players[pid] = Player(
            np.array([r[1] for r in rs]),
            np.array([r[5:] for r in rs], float),
            np.array([r[3] for r in rs]),
            np.array([r[3] == r[4] for r in rs]),
            sum(r[2] == PRIOR_SEASON for r in rs),
        )
    club = defaultdict(set)
    for d, home, away in conn.exec_driver_sql(
        """SELECT game_date, home_team_id, away_team_id FROM game
           WHERE season_type = 'regular' AND status = 'final' AND season_id = ?""",
        (SEASON,),
    ):
        club[home].add(d)
        club[away].add(d)
    club = {t: np.array(sorted(ds)) for t, ds in club.items()}
    info = conn.exec_driver_sql("SELECT player_id, full_name, positions FROM player").all()
    return (
        players,
        club,
        {r[0]: r[1] for r in info},
        {r[0]: r[2] or "unknown" for r in info},
    )


def lead_teammate_out(players: dict[int, Player]) -> set[tuple[int, str]]:
    """(player, date) pairs where the highest-usage other player on the club missed the game.
    Usage is shots, free throws and turnovers per game so far, from 10+ games with the club in
    the past three weeks, so a player traded or hurt long ago stops counting."""
    fga, fta, tov = S["fga"], S["fta"], S["tov"]
    by_team = defaultdict(lambda: defaultdict(list))
    for pid, p in players.items():
        for i in range(p.first_season, len(p.dates)):
            line = p.lines[i]
            by_team[int(p.teams[i])][p.dates[i]].append(
                (pid, line[fga] + 0.44 * line[fta] + line[tov])
            )
    out = set()
    for days in by_team.values():
        use, count, last = defaultdict(float), defaultdict(int), {}
        for d in sorted(days):
            recent = (date.fromisoformat(d) - timedelta(days=21)).isoformat()
            eligible = sorted(
                (p for p in count if count[p] >= MIN_PRIOR and last[p] >= recent),
                key=lambda p: -use[p] / count[p],
            )
            played = {p for p, _ in days[d]}
            for p in played:
                others = [q for q in eligible if q != p]
                if others and others[0] not in played:
                    out.add((p, d))
            for p, u in days[d]:
                use[p] += u
                count[p] += 1
                last[p] = d
    return out


def game_rows(players, positions, teammate_out, rng) -> tuple[list[dict], np.ndarray]:
    """One row per player and game with enough history; `u` is (rows, windows, stats)."""
    rows, us = [], []
    for pid, p in players.items():
        start = p.first_season
        for i in range(start + MIN_PRIOR, len(p.dates)):
            season = p.lines[start:i]
            priors = (season, p.lines[max(start, i - 15) : i], p.lines[max(start, i - 30) : i],
                      p.lines[:i])  # fmt: skip
            u = np.empty((len(WINDOWS), len(STATS)))
            for w, prior in enumerate(priors):
                ties = rng.random(len(STATS))
                for j in range(len(STATS)):
                    u[w, j] = rank_u(prior[:, j], p.lines[i, j], ties[j])
            d = p.dates[i]
            days = (date.fromisoformat(d) - date.fromisoformat(p.dates[i - 1])).days
            team_run = int((p.teams[start:i][::-1] == p.teams[i]).cumprod().sum())
            mean = season.mean(axis=0)
            rows.append(
                {
                    "pid": pid, "date": d, "order": i - start,
                    "mpg": mean[S["minutes"]], "ppg": mean[S["pts"]],
                    "minutes_tier": minutes_tier(mean[S["minutes"]]),
                    "scoring_tier": scoring_tier(mean[S["pts"]]),
                    "games_tier": games_tier(len(season)),
                    "position": positions.get(pid, "unknown"),
                    "experience": "first NBA season in data" if start == 0 else "veteran",
                    "period": period_of(d),
                    "venue": "home" if p.homes[i] else "away",
                    "rest": "back-to-back" if days == 1 else "1 day off" if days == 2 else "2+ days off",
                    "absence": "back after 7+ days out" if days > 7 else "no long absence",
                    "new_team": "first 5 games on a new team"
                    if team_run < min(5, i - start)
                    else "same team",
                    "lead_teammate": "lead teammate out" if (pid, d) in teammate_out
                    else "lead teammate in",
                }
            )  # fmt: skip
            us.append(u)
    return rows, np.array(us)


def week_rows(players, positions, club, horizon, rng) -> tuple[list[dict], np.ndarray, np.ndarray]:
    """One row per player and Monday. Returns rows, `u` holding production when playing, and `u`
    with missed club games counted as zeros (rows, stats)."""
    rows, played_u, padded_u = [], [], []
    for cutoff in wb.cutoffs():
        span = wb.window(cutoff, horizon)
        if span is None:
            continue
        cut, lo, hi = cutoff.isoformat(), span[0].isoformat(), span[1].isoformat()
        active = (cutoff - timedelta(days=ACTIVE_DAYS)).isoformat()
        for pid, p in players.items():
            start = p.first_season
            k = int(np.searchsorted(p.dates, cut))
            if k - start < MIN_PRIOR or p.dates[k - 1] < active:
                continue
            prior = p.lines[start:k]
            mask = (p.dates >= lo) & (p.dates <= hi)
            week = p.lines[mask]
            team = int(p.teams[k - 1])
            days = club[team]
            club_games = int(((days >= lo) & (days <= hi)).sum())
            zeros_week = max(0, club_games - len(week))
            zeros_prior = int(
                ((days >= p.dates[start]) & (days < cut)).sum()
            ) - len(prior)  # a rough count after a trade, which the floor below tolerates
            zeros_prior = max(0, zeros_prior)
            blank = np.zeros((1, len(STATS)))
            pad_prior = np.vstack([prior, np.repeat(blank, zeros_prior, axis=0)])
            pad_week = np.vstack([week, np.repeat(blank, zeros_week, axis=0)])
            if len(pad_week) == 0:
                continue
            padded = permutation_u(pad_prior, pad_week, rng, 499)
            played = permutation_u(prior, week, rng) if len(week) else np.full(len(STATS), np.nan)
            mean = prior.mean(axis=0)
            rows.append(
                {
                    "pid": pid, "date": cut, "games": len(week), "club_games": club_games,
                    "mpg": mean[S["minutes"]], "ppg": mean[S["pts"]],
                    "minutes_tier": minutes_tier(mean[S["minutes"]]),
                    "scoring_tier": scoring_tier(mean[S["pts"]]),
                    "games_tier": games_tier(len(prior)),
                    "position": positions.get(pid, "unknown"),
                    "experience": "first NBA season in data" if start == 0 else "veteran",
                    "period": period_of(cut),
                }
            )  # fmt: skip
            played_u.append(played)
            padded_u.append(padded)
    return rows, np.array(played_u), np.array(padded_u)


def prediction_rows(conn, players, espn_by_id, fmt, rng) -> list[dict]:
    """Where each model's per-game line for the coming week falls among averages of `g` of the
    player's previous games, and what happened."""
    base = list(fmt.base_stats)
    index = {s: i for i, s in enumerate(base)}
    compared = [s for s in TESTED if s in index or s == "pts"]

    def xlift_value(mean, s):
        if s == "pts":
            return 2 * mean[index["fgm"]] + mean[index["fg3m"]] + mean[index["ftm"]]
        return mean[index[s]]

    out = []
    for cutoff in wb.cutoffs():
        if wb.window(cutoff, "week+1") is None:
            continue
        cut = cutoff.isoformat()
        lo, hi = (d.isoformat() for d in wb.window(cutoff, "week+1"))
        active = (cutoff - timedelta(days=ACTIVE_DAYS)).isoformat()
        ids = [
            pid for pid, p in players.items()
            if (k := int(np.searchsorted(p.dates, cut))) - p.first_season >= MIN_PRIOR
            and p.dates[k - 1] >= active
        ]  # fmt: skip
        projected = build_projections(conn, ids, fmt, window=82, as_of=cutoff - timedelta(days=1))
        for pid in ids:
            p = players[pid]
            k = int(np.searchsorted(p.dates, cut))
            prior = p.lines[p.first_season : k]
            week = p.lines[(p.dates >= lo) & (p.dates <= hi)]
            if not len(week):
                continue
            g = len(week)
            subsets = rng.random((PERMUTATIONS, len(prior))).argsort(axis=1)[:, :g]
            means = prior[subsets].mean(axis=1)
            for s in compared:
                j = S[s]
                lines = {"xlift": xlift_value(projected[pid].mean, s)}
                if pid in espn_by_id and s in wb.L:
                    lines["espn"] = espn_by_id[pid][wb.L[s]]
                for model, line in lines.items():
                    u = (means[:, j] < line).mean() + 0.5 * (means[:, j] == line).mean()
                    out.append(
                        {
                            "pid": pid, "date": cut, "stat": s, "model": model, "games": g,
                            "mpg": prior[:, S["minutes"]].mean(), "u": float(u),
                            "line": float(line), "prior_mean": prior[:, j].mean(),
                            "actual_mean": week[:, j].mean(),
                        }
                    )  # fmt: skip
    return out


def power(players, rng, shifts=(0.0, 0.1, 0.25, 0.5), samples=400) -> list[dict]:
    """How often the tests reject when the player really has shifted, for rotation players with
    30-50 prior games: synthetic games drawn from the prior, scaled and rounded at random."""
    pool = []
    for p in players.values():
        season = p.lines[p.first_season :]
        if len(season) >= 50 and season[:, S["minutes"]].mean() >= ROTATION_MINUTES:
            pool.append(season[:40])
    out = []
    for g, label in ((1, "next game"), (3, "3-game week")):
        for shift in shifts:
            hits = np.zeros(len(STATS))
            for _ in range(samples):
                prior = pool[rng.integers(len(pool))]
                draws = prior[rng.integers(len(prior), size=g)] * (1 + shift)
                draws = np.floor(draws + rng.random(draws.shape))
                hits += p_value(permutation_u(prior, draws, rng, 299)) <= ALPHA
            for j, s in enumerate(STATS):
                out.append({"test": label, "shift": shift, "stat": s, "reject": hits[j] / samples})
    return out


def shuffled(players: dict[int, Player], rng) -> dict[int, Player]:
    """Each player's 2025-26 lines in a random order, dates kept: the null made true. Grouping
    players by their own prior averages can shift `u` by selection alone, which this measures."""
    out = {}
    for pid, p in players.items():
        lines = p.lines.copy()
        lines[p.first_season :] = rng.permutation(lines[p.first_season :], axis=0)
        out[pid] = Player(p.dates, lines, p.teams, p.homes, p.first_season)
    return out


def signal(players: dict[int, Player]) -> list[dict]:
    """How much of next game's departure from the season average does recent form explain?"""
    x, y, week_x, week_y = [], [], [], []
    for p in players.values():
        start = p.first_season
        for i in range(start + MIN_PRIOR, len(p.dates)):
            season = p.lines[start:i]
            if season[:, S["minutes"]].mean() < ROTATION_MINUTES:
                continue
            mean = season.mean(axis=0)
            recent = p.lines[max(start, i - 15) : i].mean(axis=0) - mean
            x.append(recent)
            y.append(p.lines[i] - mean)
            week = p.lines[i : i + 3]
            if len(week) == 3:
                week_x.append(recent)
                week_y.append(week.mean(axis=0) - mean)
    x, y, week_x, week_y = map(np.array, (x, y, week_x, week_y))
    out = []
    for j, s in enumerate(STATS):
        out.append(
            {
                "stat": s,
                "game_slope": float(np.polyfit(x[:, j], y[:, j], 1)[0]),
                "game_r2": float(np.corrcoef(x[:, j], y[:, j])[0, 1] ** 2),
                "3games_slope": float(np.polyfit(week_x[:, j], week_y[:, j], 1)[0]),
                "3games_r2": float(np.corrcoef(week_x[:, j], week_y[:, j])[0, 1] ** 2),
            }
        )
    return out


def summarize(u: np.ndarray, pid: np.ndarray, rng, ci: bool = False) -> dict:
    """Rejection rate, its tails and the estimated real share for one stat's tests."""
    keep = ~np.isnan(u)
    u, pid = u[keep], pid[keep]
    p = p_value(u)
    out = {
        "n": len(u),
        "reject": float((p <= ALPHA).mean()),
        "low": float((u < ALPHA / 2).mean()),
        "high": float((u > 1 - ALPHA / 2).mean()),
        "mean_u": float(u.mean()),
        "real_share": real_share(p),
    }
    if ci:
        out |= reject_ci(p <= ALPHA, pid, rng)
    return out


def reject_ci(hit: np.ndarray, pid: np.ndarray, rng, draws: int = 1000) -> dict:
    """A 95% interval resampling players, since one player's tests aren't independent."""
    ids, inv = np.unique(pid, return_inverse=True)
    hits, counts = np.bincount(inv, hit), np.bincount(inv)
    picks = rng.integers(len(ids), size=(draws, len(ids)))
    rates = hits[picks].sum(axis=1) / counts[picks].sum(axis=1)
    return {"ci_low": float(np.quantile(rates, 0.025)), "ci_high": float(np.quantile(rates, 0.975))}


def lag_correlation(frame: pl.DataFrame, u: np.ndarray) -> float:
    """Does this test's `u` predict the same player's next one? Zero if games are exchangeable."""
    a, b = [], []
    pids = frame["pid"].to_numpy()
    for i in range(1, len(pids)):
        if pids[i] == pids[i - 1] and not np.isnan(u[i]) and not np.isnan(u[i - 1]):
            a.append(u[i - 1])
            b.append(u[i])
    return float(np.corrcoef(a, b)[0, 1])


def table(frame: pl.DataFrame) -> str:
    head = "| " + " | ".join(frame.columns) + " |"
    rule = "|" + "---|" * len(frame.columns)
    body = [
        "| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in row) + " |"
        for row in frame.rows()
    ]
    return "\n".join([head, rule, *body])


def main():
    rng = np.random.default_rng(SEED)
    engine = get_engine()
    fmt = get_format("9cat_h2h")
    out, md = HERE / "output", []
    out.mkdir(exist_ok=True)
    with engine.connect() as conn:
        if not conn.exec_driver_sql(
            "SELECT COUNT(*) FROM game WHERE season_id = ?", (PRIOR_SEASON,)
        ).scalar_one():
            raise SystemExit(f"{PRIOR_SEASON} isn't loaded: see weekly_backtest.py's docstring")
        players, club, names, positions = load(conn)
        norm_ids = {wb.norm_name(names[p]): p for p in players}
        espn = wb.espn_lines(wb.fetch_espn())
        espn_by_id = {norm_ids[n]: line for n, line in espn.items() if n in norm_ids}

        teammate = lead_teammate_out(players)
        rows, gu = game_rows(players, positions, teammate, rng)
        games = pl.DataFrame(rows)
        print(f"{len(games):,} next games; {games['pid'].n_unique()} players", flush=True)

        horizons = {}
        for h in ("week+1", "weeks+1-2"):
            r, played, padded = week_rows(players, positions, club, h, rng)
            horizons[h] = (pl.DataFrame(r), played, padded)
            print(f"{h}: {len(r):,} player-weeks", flush=True)

        predicted = pl.DataFrame(prediction_rows(conn, players, espn_by_id, fmt, rng))
        print(f"{len(predicted):,} prediction tests", flush=True)

    # Headline: rotation players, each test and stat.
    rotation = (games["mpg"] >= ROTATION_MINUTES).to_numpy()
    pids = games["pid"].to_numpy()
    season_w = WINDOWS.index("season")
    records = []
    for j, s in enumerate(STATS):
        records.append(
            {"test": "next game", "stat": s,
             **summarize(gu[rotation, season_w, j], pids[rotation], rng, ci=True),
             "lag_corr": lag_correlation(games.filter(rotation), gu[rotation, season_w, j])}
        )  # fmt: skip
    for h, (frame, played, padded) in horizons.items():
        rot = (frame["mpg"] >= ROTATION_MINUTES).to_numpy()
        p = frame["pid"].to_numpy()
        ordered = frame.with_row_index("i").filter(rot).sort("pid", "date")
        idx = ordered["i"].to_numpy()
        for j, s in enumerate(STATS):
            records.append(
                {"test": f"{h}, when playing", "stat": s,
                 **summarize(played[rot, j], p[rot], rng, ci=True),
                 "lag_corr": lag_correlation(ordered, played[idx, j]) if h == "week+1" else None}
            )  # fmt: skip
            records.append(
                {"test": f"{h}, missed games as zeros", "stat": s,
                 **summarize(padded[rot, j], p[rot], rng, ci=True),
                 "lag_corr": lag_correlation(ordered, padded[idx, j]) if h == "week+1" else None}
            )  # fmt: skip
    headline = pl.DataFrame(records)
    headline.write_csv(out / "distribution_headline.csv")
    md.append("## Rotation players (20+ min), season-to-date distribution\n")
    for test in headline["test"].unique(maintain_order=True):
        md += [f"\n### {test}\n", table(headline.filter(pl.col("test") == test).drop("test"))]

    # Does a shorter or longer history fit better?
    win = []
    for w, name in enumerate(WINDOWS):
        for j, s in enumerate(STATS):
            win.append({"window": name, "stat": s, **summarize(gu[rotation, w, j], pids[rotation], rng)})
    win = pl.DataFrame(win)
    win.write_csv(out / "distribution_windows.csv")
    md += ["\n## Next game by history used (rotation players): rejection rate\n",
           table(win.pivot(on="window", index="stat", values="reject"))]  # fmt: skip

    # Segments: who and when. Next game keeps its context columns; weeks the player ones.
    game_segments = ("minutes_tier", "scoring_tier", "position", "experience", "games_tier",
                     "period", "venue", "rest", "absence", "new_team", "lead_teammate")  # fmt: skip
    seg_rows = []
    week_frame, week_played, _ = horizons["week+1"]
    week_pids = week_frame["pid"].to_numpy()
    for seg in game_segments:
        values = games[seg].to_numpy()
        for v in np.unique(values):
            mask = values == v
            if seg != "minutes_tier":
                mask = mask & rotation
            for j, s in enumerate(STATS):
                seg_rows.append(
                    {"test": "next game", "segment": seg, "value": str(v), "stat": s,
                     **summarize(gu[mask, season_w, j], pids[mask], rng)}
                )  # fmt: skip
        if seg in week_frame.columns:
            wv = week_frame[seg].to_numpy()
            wrot = (week_frame["mpg"] >= ROTATION_MINUTES).to_numpy()
            for v in np.unique(wv):
                mask = wv == v
                if seg != "minutes_tier":
                    mask = mask & wrot
                for j, s in enumerate(STATS):
                    seg_rows.append(
                        {"test": "week+1", "segment": seg, "value": str(v), "stat": s,
                         **summarize(week_played[mask, j], week_pids[mask], rng)}
                    )  # fmt: skip
    segments = pl.DataFrame(seg_rows)
    segments.write_csv(out / "distribution_segments.csv")
    tested = segments.filter(pl.col("stat") != "minutes")
    for test in ("next game", "week+1"):
        part = tested.filter(pl.col("test") == test)
        md.append(f"\n## {test}: mean across stats, rotation players (all players for minutes tier)\n")
        avg = part.group_by("segment", "value", maintain_order=True).agg(
            pl.col("n").max(), pl.col("reject").mean(), pl.col("low").mean(),
            pl.col("high").mean(), pl.col("mean_u").mean(), pl.col("real_share").mean(),
        )  # fmt: skip
        md.append(table(avg))
        md.append(f"\n### {test}: rejection rate by stat and segment\n")
        wide = part.pivot(on="stat", index=["segment", "value"], values="reject")
        md.append(table(wide))
        md.append(f"\n### {test}: mean position by stat and segment (0.5 means no shift)\n")
        wide = part.pivot(on="stat", index=["segment", "value"], values="mean_u")
        md.append(table(wide))

    # Individual player-stat pairs: over the season, are the ranks uniform?
    pair_rows = []
    order = games.with_row_index("i").sort("pid", "date")
    idx_by_pid = order.partition_by("pid", as_dict=True)
    for (pid,), part in idx_by_pid.items():
        i = part["i"].to_numpy()
        if len(i) < 30 or part["mpg"].to_numpy().mean() < ROTATION_MINUTES:
            continue
        p = players[pid]
        first = p.first_season
        season = p.lines[first:]
        third = len(season) // 3
        for j, s in enumerate(STATS):
            pair_rows.append(
                {
                    "pid": pid, "player": names.get(pid, str(pid)), "stat": s, "games": len(i),
                    "p": float(kstest(gu[i, season_w, j], "uniform").pvalue),
                    "mean_u": float(gu[i, season_w, j].mean()),
                    "first_third": float(season[:third, j].mean()),
                    "last_third": float(season[-third:, j].mean()),
                    "reject": float((p_value(gu[i, season_w, j]) <= ALPHA).mean()),
                }
            )  # fmt: skip
    pairs = pl.DataFrame(pair_rows)
    tested_pairs = pairs.filter(pl.col("stat") != "minutes")
    kept = bh_reject(tested_pairs["p"].to_numpy())
    tested_pairs = tested_pairs.with_columns(pl.Series("significant", kept))
    tested_pairs.write_csv(out / "distribution_player_stats.csv")
    by_stat = tested_pairs.group_by("stat", maintain_order=True).agg(
        pl.len().alias("players"), pl.col("significant").mean().alias("share_significant"),
        (pl.col("p") <= ALPHA).mean().alias("share_p05"),
    )  # fmt: skip
    md += [f"\n## Player-stat pairs (season KS test, FDR 5%, {pairs['pid'].n_unique()} players)\n",
           table(by_stat),
           "\nStrongest departures\n",
           table(tested_pairs.sort("p").head(25).select(
               "player", "stat", "games", "p", "mean_u", "first_third", "last_third"))]  # fmt: skip
    per_player = tested_pairs.group_by("player").agg(pl.col("significant").sum().alias("stats_significant"))
    counts = per_player.group_by("stats_significant").len().sort("stats_significant")
    md += ["\nStats significant per player\n", table(counts)]

    # The prediction itself against the distribution.
    predicted = predicted.filter(pl.col("mpg") >= ROTATION_MINUTES).with_columns(
        (2 * pl.min_horizontal(pl.col("u"), 1 - pl.col("u"))).alias("p_line"),
        (pl.col("line") - pl.col("prior_mean")).alias("shift"),
        (pl.col("actual_mean") - pl.col("prior_mean")).alias("outcome"),
    )
    predicted.write_csv(out / "distribution_predictions.csv")
    pred_rows = []
    for (model, stat), part in predicted.group_by("model", "stat", maintain_order=True):
        strong = part.filter(pl.col("p_line") <= ALPHA)
        shift, outcome = part["shift"].to_numpy(), part["outcome"].to_numpy()
        follows = (np.sign(strong["shift"].to_numpy()) == np.sign(strong["outcome"].to_numpy()))
        err_line = np.abs(part["line"].to_numpy() - part["actual_mean"].to_numpy()).mean()
        err_prior = np.abs(part["prior_mean"].to_numpy() - part["actual_mean"].to_numpy()).mean()
        pred_rows.append(
            {
                "model": model, "stat": stat, "n": len(part),
                "share_line_significant": len(strong) / len(part),
                "follows_when_significant": float(follows.mean()) if len(strong) else float("nan"),
                "slope_outcome_on_shift": float(np.polyfit(shift, outcome, 1)[0]),
                "mae_line": float(err_line), "mae_season_mean": float(err_prior),
            }
        )  # fmt: skip
    preds = pl.DataFrame(pred_rows).sort("model", "stat")
    preds.write_csv(out / "distribution_prediction_summary.csv")
    md += ["\n## Predicted week against the distribution (rotation players, week+1)\n", table(preds)]

    # What the tests could detect.
    detect = pl.DataFrame(power(players, rng))
    detect.write_csv(out / "distribution_power.csv")
    for label in ("next game", "3-game week"):
        wide = detect.filter(pl.col("test") == label).pivot(on="shift", index="stat", values="reject")
        md += [f"\n## Power: rejection rate by real shift ({label}, 40 prior games)\n", table(wide)]

    # Recent form as a signal.
    form = pl.DataFrame(signal(players))
    form.write_csv(out / "distribution_signal.csv")
    md += ["\n## Departure from the season average explained by the last 15 games\n", table(form)]

    # The placebo: the same analysis with each player's games shuffled.
    fake = shuffled(players, rng)
    fake_rows, fake_u = game_rows(fake, positions, teammate, rng)
    fake_games = pl.DataFrame(fake_rows)
    fake_week, fake_played, _ = week_rows(fake, positions, club, "week+1", rng)
    fake_week = pl.DataFrame(fake_week)
    fake_rot = (fake_games["mpg"] >= ROTATION_MINUTES).to_numpy()
    fake_pids = fake_games["pid"].to_numpy()
    week_rot = (fake_week["mpg"] >= ROTATION_MINUTES).to_numpy()
    week_ids = fake_week["pid"].to_numpy()
    ordered = fake_week.with_row_index("i").filter(week_rot).sort("pid", "date")
    placebo = []
    for j, s in enumerate(STATS):
        placebo.append(
            {"test": "next game", "stat": s,
             **summarize(fake_u[fake_rot, season_w, j], fake_pids[fake_rot], rng),
             "lag_corr": lag_correlation(fake_games.filter(fake_rot), fake_u[fake_rot, season_w, j])}
        )  # fmt: skip
        placebo.append(
            {"test": "week+1", "stat": s,
             **summarize(fake_played[week_rot, j], week_ids[week_rot], rng),
             "lag_corr": lag_correlation(ordered, fake_played[ordered["i"].to_numpy(), j])}
        )  # fmt: skip
    placebo = pl.DataFrame(placebo)
    placebo.write_csv(out / "distribution_placebo.csv")
    md.append("\n## Placebo: each player's games shuffled\n")
    for test in ("next game", "week+1"):
        md += [f"\n### {test}\n", table(placebo.filter(pl.col("test") == test).drop("test"))]
    fake_seg = []
    for seg in ("minutes_tier", "scoring_tier", "experience", "position", "games_tier"):
        for frame, u, rot, label in (
            (fake_games, fake_u[:, season_w], fake_rot, "next game"),
            (fake_week, fake_played, week_rot, "week+1"),
        ):
            values = frame[seg].to_numpy()
            ids = frame["pid"].to_numpy()
            for v in np.unique(values):
                mask = values == v if seg == "minutes_tier" else (values == v) & rot
                stats = [summarize(u[mask, j], ids[mask], rng) for j in range(1, len(STATS))]
                fake_seg.append(
                    {"test": label, "segment": seg, "value": str(v), "n": stats[0]["n"],
                     "reject": float(np.mean([x["reject"] for x in stats])),
                     "mean_u": float(np.mean([x["mean_u"] for x in stats]))}
                )  # fmt: skip
    fake_seg = pl.DataFrame(fake_seg)
    fake_seg.write_csv(out / "distribution_placebo_segments.csv")
    md += ["\n### Placebo by segment\n", table(fake_seg)]

    summary = "\n".join(md)
    (out / "distribution_summary.md").write_text(summary)
    print(summary)


if __name__ == "__main__":
    main()
