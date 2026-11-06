"""Does a t-test tell next week's games apart from the player's past games? (ccsv-rumble #33)

Every Monday of 2025-26, for each rotation player and stat, the coming week's games are tested
against a distribution built from the games before that Monday:

- **last X games**, equally weighted, for X = 5, 10, 15, 30, the season so far, and up to 82
  games reaching into 2024-25;
- **recency-weighted** over up to 82 games: game j games ago weighs 0.5^(j / half-life), and a
  2024-25 game also weighs 0.25, as xlift does. The half-life of 40 is xlift's;
- **xlift (shipped)**: ``build_projections``'s mean and spread, shrinkage included.

Two tests per player-week and stat:

- **prediction t**: t = (week mean - mean) / (sd * sqrt(1/n + 1/g)), df = n - 1, with n the past
  games' (effective) count and g the week's games. The week's spread is taken from the past games,
  so a one-game week can be tested;
- **Welch**: the textbook two-sample test, with the week's own spread, for weeks of 2+ games.

Weighted distributions use the weighted mean and variance and Kish's effective n. The week is the
games actually played, so this tests the per-game distribution, not availability.

A t-test assumes normal data, and these counts aren't, so the same analysis is run with each
player's games shuffled. That makes the null true, and its rejection rate is the real baseline
in place of 5%. Uses the database copy described in weekly_backtest.py:

    (cd analysis && uv run python ttest_backtest.py)
"""

from datetime import timedelta
from pathlib import Path

import numpy as np
import polars as pl
from ffmodel.contract.db import get_engine
from ffmodel.core.model import build_projections
from ffmodel.core.scoring import get_format
from scipy import stats as sps

import distribution_test as dt
import weekly_backtest as wb

TESTED = dt.TESTED
S = dt.S
ALPHA = 0.05
SEASON_WEIGHT = 0.25  # xlift's weight for each season of age
CONFIGS = (
    ("last 5", "window", 5), ("last 10", "window", 10), ("last 15", "window", 15),
    ("last 30", "window", 30), ("season", "season", None), ("last 82", "window", 82),
    ("weighted, half-life 5", "weighted", 5), ("weighted, half-life 10", "weighted", 10),
    ("weighted, half-life 20", "weighted", 20), ("weighted, half-life 40 (xlift)", "weighted", 40),
)  # fmt: skip
XLIFT = "xlift (shipped)"
HERE = Path(__file__).parent


def weights(n_season: int, n_before: int, kind: str, param) -> np.ndarray:
    """Weights for the past games, most recent first: `n_season` from this season, then
    `n_before` from last season. Zero means the game is left out."""
    n = n_season + n_before
    w = np.zeros(n)
    if kind == "season":
        w[:n_season] = 1
    elif kind == "window":
        w[: min(param, n)] = 1
    else:
        k = min(82, n)
        w[:k] = 0.5 ** (np.arange(k) / param)
        w[n_season:k] *= SEASON_WEIGHT
    return w


def weighted_moments(x: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Mean, unbiased variance and Kish's effective count of `x` (games, stats) under `w`."""
    keep = w > 0
    x, w = x[keep], w[keep]
    v1, v2 = w.sum(), (w**2).sum()
    mean = (w[:, None] * x).sum(axis=0) / v1
    var = (w[:, None] * (x - mean) ** 2).sum(axis=0) / (v1 - v2 / v1)
    return mean, var, v1**2 / v2


def prediction_t(week: np.ndarray, mean, var, n_eff: float) -> np.ndarray:
    """Two-sided p per stat for the week's mean against the distribution, the week's spread taken
    from the distribution. A zero-spread stat is significant if the week differs at all."""
    g = len(week)
    diff = week.mean(axis=0) - mean
    se = np.sqrt(var * (1 / n_eff + 1 / g))
    with np.errstate(divide="ignore", invalid="ignore"):
        t = diff / se
        p = 2 * sps.t.sf(np.abs(t), df=max(n_eff - 1, 1))
    return np.where(se > 0, p, np.where(np.isclose(diff, 0), 1.0, 0.0))


def welch(week: np.ndarray, mean, var, n_eff: float) -> np.ndarray:
    """Welch's two-sample p per stat, the week's own spread included. Needs two or more games."""
    g = len(week)
    wvar = week.var(axis=0, ddof=1)
    a, b = var / n_eff, wvar / g
    se = np.sqrt(a + b)
    diff = week.mean(axis=0) - mean
    with np.errstate(divide="ignore", invalid="ignore"):
        df = (a + b) ** 2 / (a**2 / max(n_eff - 1, 1) + b**2 / (g - 1))
        p = 2 * sps.t.sf(np.abs(diff / se), df=np.where(np.isfinite(df), df, 1))
    return np.where(se > 0, p, np.where(np.isclose(diff, 0), 1.0, 0.0))


def xlift_moments(proj, base: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """The shipped projection's per-game mean and variance in STATS order; NaN where xlift has no
    such stat (minutes, 3PA)."""
    index = {s: i for i, s in enumerate(base)}
    cov = proj.chol @ proj.chol.T if proj.chol is not None else np.diag(proj.mean_stderr**2)
    mean, var = np.full(len(dt.STATS), np.nan), np.full(len(dt.STATS), np.nan)
    for s in dt.STATS:
        if s in index:
            mean[S[s]], var[S[s]] = proj.mean[index[s]], cov[index[s], index[s]]
    a = np.zeros(len(base))
    a[index["fgm"]], a[index["fg3m"]], a[index["ftm"]] = 2, 1, 1
    mean[S["pts"]], var[S["pts"]] = a @ proj.mean, a @ cov @ a
    return mean, var


def tests(players, horizon: str, projections=None) -> list[dict]:
    """One row per player-week, test, distribution and stat."""
    rows = []
    for cutoff in wb.cutoffs():
        span = wb.window(cutoff, horizon)
        if span is None:
            continue
        cut, lo, hi = cutoff.isoformat(), span[0].isoformat(), span[1].isoformat()
        active = (cutoff - timedelta(days=dt.ACTIVE_DAYS)).isoformat()
        for pid, p in players.items():
            start = p.first_season
            k = int(np.searchsorted(p.dates, cut))
            if k - start < dt.MIN_PRIOR or p.dates[k - 1] < active:
                continue
            season = p.lines[start:k]
            mpg = season[:, S["minutes"]].mean()
            if mpg < dt.ROTATION_MINUTES:
                continue
            week = p.lines[(p.dates >= lo) & (p.dates <= hi)]
            if not len(week):
                continue
            past = p.lines[:k][::-1]  # most recent first
            key = {
                "pid": pid, "date": cut, "games": len(week), "mpg": mpg,
                "minutes_tier": dt.minutes_tier(mpg),
                "scoring_tier": dt.scoring_tier(season[:, S["pts"]].mean()),
                "experience": "first season in data" if start == 0 else "veteran",
            }  # fmt: skip
            dists = []
            for name, kind, param in CONFIGS:
                w = weights(k - start, start, kind, param)
                dists.append((name, *weighted_moments(past, w)))
            if projections is not None and pid in projections.get(cut, {}):
                proj = projections[cut][pid]
                mean, var = xlift_moments(proj, projections["base"])
                dists.append((XLIFT, mean, var, proj.n_eff))
            for name, mean, var, n_eff in dists:
                results = {"prediction t": prediction_t(week, mean, var, n_eff)}
                if len(week) >= 2:
                    results["welch"] = welch(week, mean, var, n_eff)
                err = week.mean(axis=0) - mean
                for test, pvals in results.items():
                    for s in TESTED:
                        j = S[s]
                        if np.isnan(mean[j]):
                            continue
                        rows.append(
                            {**key, "dist": name, "test": test, "stat": s, "p": float(pvals[j]),
                             "err": float(err[j]), "n_eff": float(n_eff)}
                        )  # fmt: skip
    return rows


def project(conn, players, fmt) -> dict:
    """The shipped projection at every Monday, for the players the tests can use."""
    out = {"base": list(fmt.base_stats)}
    for cutoff in wb.cutoffs():
        cut = cutoff.isoformat()
        ids = [
            pid for pid, p in players.items()
            if int(np.searchsorted(p.dates, cut)) - p.first_season >= dt.MIN_PRIOR
        ]  # fmt: skip
        out[cut] = build_projections(conn, ids, fmt, window=82, as_of=cutoff - timedelta(days=1))
        print(f"projected {cut}", flush=True)
    return out


def summary(real: pl.DataFrame, fake: pl.DataFrame, by: list[str]) -> pl.DataFrame:
    """Rejection rate against the shuffled baseline, plus each distribution's error."""
    agg = [
        pl.len().alias("n"),
        (pl.col("p") <= ALPHA).mean().alias("significant"),
        pl.col("err").abs().mean().alias("mae"),
        pl.col("err").mean().alias("bias"),
    ]
    r = real.group_by(by).agg(agg)
    f = fake.group_by(by).agg((pl.col("p") <= ALPHA).mean().alias("shuffled"))
    return r.join(f, on=by, how="left").with_columns(
        (pl.col("significant") - pl.col("shuffled")).alias("excess")
    )


def ordered(frame: pl.DataFrame) -> pl.DataFrame:
    names = [c[0] for c in CONFIGS] + [XLIFT]
    order = pl.DataFrame({"dist": names}).with_row_index("o")
    return frame.join(order, on="dist").sort("o").drop("o")


def main():
    rng = np.random.default_rng(dt.SEED)
    fmt = get_format("9cat_h2h")
    out, md = HERE / "output", []
    out.mkdir(exist_ok=True)
    with get_engine().connect() as conn:
        players, _, _, _ = dt.load(conn)
        projections = project(conn, players, fmt)
    real = {h: pl.DataFrame(tests(players, h, projections)) for h in ("week+1", "weeks+1-2")}
    fake_players = dt.shuffled(players, rng)
    fake = {h: pl.DataFrame(tests(fake_players, h)) for h in ("week+1", "weeks+1-2")}
    for h, frame in real.items():
        frame.write_csv(out / f"ttest_{h}.csv")

    for h in ("week+1", "weeks+1-2"):
        r, f = real[h], fake[h]
        for test in ("prediction t", "welch"):
            rt, ft = r.filter(pl.col("test") == test), f.filter(pl.col("test") == test)
            both = summary(rt, ft, ["dist"])
            weeks = rt.select(pl.struct("pid", "date").n_unique()).item()
            md += [f"\n## {h}, {test}: all stats ({weeks:,} player-weeks)\n",
                   dt.table(ordered(both.drop("mae", "bias")))]  # fmt: skip
            per = summary(rt, ft, ["dist", "stat"])
            for metric in ("significant", "excess"):
                wide = per.pivot(on="stat", index="dist", values=metric).select("dist", *TESTED)
                md += [f"\n### {h}, {test}: {metric} by stat\n", dt.table(ordered(wide))]
            if test == "prediction t":
                wide = per.pivot(on="stat", index="dist", values="mae").select("dist", *TESTED)
                md += [f"\n### {h}: error of the distribution's mean (per game) by stat\n",
                       dt.table(ordered(wide))]  # fmt: skip

    r1 = real["week+1"].filter(pl.col("test") == "prediction t")
    f1 = fake["week+1"].filter(pl.col("test") == "prediction t")
    keep = ["season", "last 15", "weighted, half-life 10", "weighted, half-life 40 (xlift)", XLIFT]
    for seg in ("minutes_tier", "scoring_tier", "experience", "games"):
        part = summary(r1, f1, ["dist", seg]).filter(pl.col("dist").is_in(keep))
        wide = part.pivot(on="dist", index=seg, values="excess").sort(seg)
        md += [f"\n## week+1, prediction t: excess over shuffled by {seg}\n", dt.table(wide)]

    text = "\n".join(md)
    (out / "ttest_summary.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
