"""Why is the strategic H2H overconfident? The measurements behind h2h_calibration_analysis.py.

Each week is tested with projections from the day before it starts, against box scores of the
league's current active rosters (moves made during a week count as made before it; injury tags
are today's). Week 2's own league totals check how far that rebuild is from the real thing.
Issue #6.
"""

from dataclasses import dataclass
from datetime import date

import numpy as np
import polars as pl
from sqlalchemy import text

from ffmodel.core import cache
from ffmodel.core.data import get_league, get_matchup_state
from ffmodel.core.model import fragility
from ffmodel.core.scenario import from_snapshot
from ffmodel.core.scoring import get_format
from ffmodel.tools.impact_analysis.settings import AnalysisSettings

ITER = 10_000
GAMES_PER_WEEK = 3  # the strategic simulation's week


@dataclass(frozen=True)
class Window:
    label: str
    as_of: date  # projections use games through this day
    start: date
    end: date


@dataclass
class League:
    conn: object
    scenario: object
    fmt: object
    stats: list[str]
    categories: list[str]
    direction: np.ndarray
    statuses: dict
    names: dict  # player id -> name
    team_names: dict
    active: dict  # team -> active player ids
    teams: list[int]


def load(conn, league_id: int = 1) -> League:
    snap = get_league(conn, league_id)
    scenario = from_snapshot(snap)
    fmt = get_format(snap.settings.scoring_format_id)
    teams = sorted(scenario.rosters)
    return League(
        conn=conn,
        scenario=scenario,
        fmt=fmt,
        stats=list(fmt.base_stats),
        categories=[c.label for c in fmt.categories],
        direction=np.array([1 if c.higher_is_better else -1 for c in fmt.categories]),
        statuses={r.player.player_id: r.status for t in snap.teams for r in t.roster},
        names={r.player.player_id: r.player.full_name for t in snap.teams for r in t.roster},
        team_names={t.fantasy_team_id: t.name for t in snap.teams},
        active={t: list(scenario.active_players(t)) for t in teams},
        teams=teams,
    )


def everyone(lg: League) -> list[int]:
    return [p for t in lg.teams for p in lg.active[t]]


def projections(lg: League, as_of: date, option: str = "dab_tag") -> dict:
    cache.clear()
    s = AnalysisSettings(league_id=1, team_id=lg.teams[0], as_of=as_of)
    raw = cache.projections(lg.conn, everyone(lg), lg.fmt, s)
    return fragility.apply(option, raw, lg.scenario, lg.statuses, lg.conn, as_of)


def box_scores(lg: League, w: Window) -> dict[int, tuple[int, np.ndarray]]:
    """{player: (games played, summed base stats)} in the window."""
    sums = ", ".join(f"SUM(pg.{s}) {s}" for s in lg.stats)
    rows = lg.conn.execute(
        text(
            f"SELECT pg.player_id, COUNT(*) n, {sums} FROM player_game pg JOIN game g USING (game_id)"
            " WHERE g.game_date BETWEEN :a AND :b AND COALESCE(pg.minutes, 0) > 0"
            " GROUP BY pg.player_id"
        ),
        {"a": w.start.isoformat(), "b": w.end.isoformat()},
    ).mappings()
    return {r["player_id"]: (r["n"], np.array([r[s] or 0 for s in lg.stats], float)) for r in rows}


def scheduled(lg: League, w: Window) -> dict[int, int]:
    """Games each player's NBA team had in the window (by his current team)."""
    rows = lg.conn.execute(
        text(
            "SELECT p.player_id, COUNT(g.game_id) FROM player p JOIN game g"
            " ON g.home_team_id = p.current_team_id OR g.away_team_id = p.current_team_id"
            " WHERE g.game_date BETWEEN :a AND :b GROUP BY p.player_id"
        ),
        {"a": w.start.isoformat(), "b": w.end.isoformat()},
    ).all()
    return dict(rows)


def category_values(lg: League, totals: np.ndarray) -> np.ndarray:
    d = {s: totals[..., i] for i, s in enumerate(lg.stats)}
    for name, fn in lg.fmt.derived_stats.items():
        d[name] = fn(d)
    return lg.fmt.category_values(d)


def team_actual(lg: League, team: int, box: dict) -> np.ndarray:
    return sum((box[p][1] for p in lg.active[team] if p in box), np.zeros(len(lg.stats)))


# --- 1. Availability ------------------------------------------------------------------------------


def availability(lg: League, w: Window) -> pl.DataFrame:
    """Per active player: predicted availability (three options) vs share of games played."""
    box, sched = box_scores(lg, w), scheduled(lg, w)
    out = {opt: projections(lg, w.as_of, opt) for opt in ("dab", "dab_tag", "last15")}
    rows = []
    for p in everyone(lg):
        if not sched.get(p):
            continue
        pr = out["dab"].get(p)
        rows.append(
            {
                "week": w.label,
                "player": lg.names.get(p, str(p)),
                "status": lg.statuses.get(p),
                "history": pr.games_found if pr else 0,
                "dAB": (pr.availability or 0.0) if pr else 0.0,
                "dAB × tag": (out["dab_tag"][p].availability or 0.0) if p in out["dab_tag"] else 0.0,
                "Last 15": (out["last15"][p].availability or 0.0) if p in out["last15"] else 0.0,
                "played": box.get(p, (0, None))[0] / sched[p],
            }
        )
    return pl.DataFrame(rows)


# --- 2. Games per team ------------------------------------------------------------------------------


def games(lg: League, w: Window) -> pl.DataFrame:
    proj, box, sched = projections(lg, w.as_of), box_scores(lg, w), scheduled(lg, w)
    rows = []
    for t in lg.teams:
        avail = [(proj[p].availability or 0.0) if p in proj else 0.0 for p in lg.active[t]]
        rows.append(
            {
                "week": w.label,
                "team": lg.team_names[t],
                "app expects": GAMES_PER_WEEK * sum(avail),
                "schedule × dAB": sum(sched.get(p, 0) * a for p, a in zip(lg.active[t], avail, strict=True)),
                "actual": sum(box.get(p, (0, None))[0] for p in lg.active[t]),
            }
        )
    return pl.DataFrame(rows)


# --- 3. Per-game spread -------------------------------------------------------------------------


def per_game_z(lg: League, w: Window) -> pl.DataFrame:
    """Each player's window totals given his actual games, in units of the model's spread: once
    with the per-game mean taken as exact (as the simulation does), once adding its standard error."""
    proj, box = projections(lg, w.as_of), box_scores(lg, w)
    rows = []
    for p in everyone(lg):
        pr = proj.get(p)
        if pr is None or pr.chol is None or p not in box:
            continue
        n, total = box[p]
        var = n * np.diag(pr.chol @ pr.chol.T)
        miss = total - n * pr.mean
        for i, s in enumerate(lg.stats):
            rows.append(
                {
                    "week": w.label,
                    "stat": s,
                    "mean taken as exact": miss[i] / np.sqrt(max(var[i], 1e-9)),
                    "with its uncertainty": miss[i] / np.sqrt(max(var[i] + n**2 * pr.mean_stderr[i] ** 2, 1e-9)),
                }
            )
    return pl.DataFrame(rows)


# --- 4. Team-week coverage and rescoring ---------------------------------------------------------


def _simulate(lg, team, proj, games_of, sd_scale=1.0, se_scale=0.0, seed=0) -> np.ndarray:
    rng = np.random.default_rng([seed, team])
    raw = np.zeros((ITER, len(lg.stats)))
    for p in lg.active[team]:
        pr = proj.get(p)
        if pr is None or pr.chol is None:
            continue
        k = games_of(p, pr, rng)
        mu = pr.mean[None, :] + se_scale * rng.standard_normal((ITER, len(lg.stats))) * pr.mean_stderr
        z = rng.standard_normal((ITER, len(lg.stats)))
        raw += k[:, None] * mu + sd_scale * np.sqrt(k)[:, None] * (z @ pr.chol.T)
    raw = np.rint(np.clip(raw, 0, None))
    for small, big in lg.fmt.subset_constraints:
        i, j = lg.stats.index(small), lg.stats.index(big)
        raw[:, i] = np.minimum(raw[:, i], raw[:, j])
    return category_values(lg, raw)


def _app_games(p, pr, rng):
    return rng.binomial(GAMES_PER_WEEK, pr.availability or 0.0, ITER).astype(float)


def coverage(lg: League, w: Window) -> pl.DataFrame:
    """Per team and category: where the actual week fell in the simulated distribution
    (0.5 = the middle; inside 0.1–0.9 = inside the 80% range)."""
    proj, box = projections(lg, w.as_of), box_scores(lg, w)
    variants = {
        "app (3 games × dAB)": dict(games_of=_app_games),
        "actual games": dict(games_of=lambda p, pr, rng: np.full(ITER, float(box.get(p, (0, None))[0]))),
        "actual games + mean uncertainty": dict(
            games_of=lambda p, pr, rng: np.full(ITER, float(box.get(p, (0, None))[0])), se_scale=1.0
        ),
    }
    rows = []
    for t in lg.teams:
        actual = category_values(lg, team_actual(lg, t, box))
        for name, kw in variants.items():
            sim = _simulate(lg, t, proj, **kw)
            pit = np.nanmean(sim < actual, axis=0) + 0.5 * np.nanmean(sim == actual, axis=0)
            for c, v in zip(lg.categories, pit, strict=True):
                rows.append({"week": w.label, "variant": name, "team": t, "category": c, "position": v})
    return pl.DataFrame(rows)


def rescore(lg: League, w: Window, pairs: list[tuple[int, int]]) -> pl.DataFrame:
    """Re-score a week's matchups under model variants, against rebuilt actual totals."""
    proj, box, sched = projections(lg, w.as_of), box_scores(lg, w), scheduled(lg, w)

    def sched_games(p, pr, rng):
        return rng.binomial(sched.get(p, 0), pr.availability or 0.0, ITER).astype(float)

    def sched_healthy(p, pr, rng):
        healthy = lg.statuses.get(p) in (None, "healthy")
        return rng.binomial(sched.get(p, 0), 0.9 if healthy else (pr.availability or 0.0), ITER).astype(float)

    variants = {
        "app as shipped": dict(games_of=_app_games),
        "+ NBA schedule": dict(games_of=sched_games),
        "+ wider per-game spread (×1.2)": dict(games_of=sched_games, sd_scale=1.2),
        "+ mean uncertainty (×2 s.e.)": dict(games_of=sched_games, sd_scale=1.2, se_scale=2.0),
        "+ healthy players at 90%": dict(games_of=sched_healthy, sd_scale=1.2, se_scale=2.0),
    }
    rows = []
    for name, kw in variants.items():
        cat_brier, called, match_brier, fav = [], [], [], 0
        for a, b in pairs:
            d = (_simulate(lg, a, proj, **kw) - _simulate(lg, b, proj, **kw)) * lg.direction
            pw = np.nanmean(d > 0, axis=0) + 0.5 * np.nanmean(d == 0, axis=0)
            dd = (category_values(lg, team_actual(lg, a, box)) - category_values(lg, team_actual(lg, b, box))) * lg.direction
            won = np.where(dd > 0, 1.0, np.where(dd < 0, 0.0, 0.5))
            cat_brier += list((pw - won) ** 2)
            called += [w_ if p_ >= 0.8 else 1 - w_ for p_, w_ in zip(pw, won, strict=True) if p_ >= 0.8 or p_ <= 0.2]
            wins, losses = np.sum(d > 0, axis=1), np.sum(d < 0, axis=1)
            pm = np.mean(wins > losses) + 0.5 * np.mean(wins == losses)
            mw = 1.0 if (dd > 0).sum() > (dd < 0).sum() else 0.0 if (dd > 0).sum() < (dd < 0).sum() else 0.5
            match_brier.append((pm - mw) ** 2)
            fav += (pm > 0.5) == (mw == 1.0)
        rows.append(
            {
                "model": name,
                "category Brier": float(np.mean(cat_brier)),
                "confident calls that held": float(np.mean(called)) if called else float("nan"),
                "matchup Brier": float(np.mean(match_brier)),
                "favorites won": f"{fav} of {len(pairs)}",
            }
        )
    return pl.DataFrame(rows)


# --- 5. How good is the rebuild? ----------------------------------------------------------------


def rebuild_check(lg: League, league_id: int = 1) -> tuple[pl.DataFrame, int, int, Window]:
    """The current week so far, rebuilt from active rosters and box scores, vs the league's own
    totals: error per stat, and category winners that agree."""
    state = get_matchup_state(lg.conn, league_id)
    w = Window("current week", state.period_start, state.period_start, state.as_of)
    box = box_scores(lg, w)
    real = {
        r["fantasy_team_id"]: r
        for r in lg.conn.execute(
            text("SELECT * FROM matchup_team WHERE league_id = :l"), {"l": league_id}
        ).mappings()
    }
    cols = ["pts", "reb", "ast", "stl", "blk", "fg3m", "fgm", "ftm", "tov"]
    errs = {c: [] for c in cols}
    for t in lg.teams:
        d = dict(zip(lg.stats, team_actual(lg, t, box), strict=True))
        d["pts"] = 2 * d["fgm"] + d["fg3m"] + d["ftm"]
        for c in cols:
            if real[t][c]:
                errs[c].append(abs(d[c] - real[t][c]) / real[t][c])
    agree = total = 0
    for t in lg.teams:
        o = real[t]["opponent_team_id"]
        if t > o:
            continue
        mine = category_values(lg, team_actual(lg, t, box)) - category_values(lg, team_actual(lg, o, box))
        theirs = category_values(lg, np.array([real[t][s] for s in lg.stats], float)) - category_values(
            lg, np.array([real[o][s] for s in lg.stats], float)
        )
        agree += int((np.sign(mine * lg.direction) == np.sign(theirs * lg.direction)).sum())
        total += len(lg.categories)
    df = pl.DataFrame({"stat": cols, "error": [float(np.mean(errs[c])) for c in cols]})
    return df, agree, total, w


# --- 6. The worst misses --------------------------------------------------------------------------


def team_breakdown(lg: League, w: Window, team: int) -> tuple[dict, pl.DataFrame]:
    """A team's expected vs actual games and points, and its players."""
    proj, box = projections(lg, w.as_of), box_scores(lg, w)
    fgm, fg3m, ftm = (lg.stats.index(s) for s in ("fgm", "fg3m", "ftm"))
    rows, eg, ep, ag, ap = [], 0.0, 0.0, 0, 0.0
    for p in lg.active[team]:
        pr = proj.get(p)
        a = (pr.availability or 0.0) if pr else 0.0
        per_pts = (2 * pr.mean[fgm] + pr.mean[fg3m] + pr.mean[ftm]) if pr is not None and pr.chol is not None else 0.0
        n, tot = box.get(p, (0, np.zeros(len(lg.stats))))
        pts = 2 * tot[fgm] + tot[fg3m] + tot[ftm]
        eg, ep, ag, ap = eg + GAMES_PER_WEEK * a, ep + GAMES_PER_WEEK * a * per_pts, ag + n, ap + pts
        rows.append(
            {
                "player": lg.names.get(p, str(p)),
                "tag today": lg.statuses.get(p),
                "history (games)": pr.games_found if pr else 0,
                "dAB × tag": a,
                "games expected": GAMES_PER_WEEK * a,
                "games played": n,
                "points expected": GAMES_PER_WEEK * a * per_pts,
                "points scored": pts,
            }
        )
    summary = {"games expected": eg, "games played": ag, "points expected": ep, "points scored": ap}
    df = pl.DataFrame(rows).with_columns(
        pl.col("dAB × tag").round(2),
        pl.col("games expected").round(1),
        pl.col("points expected", "points scored").round(0).cast(pl.Int64),
    )
    return summary, df.sort("games played", descending=True)
