"""Backtest for 006 recency-weighted projections: checks SC-001, SC-002, SC-003 and SC-007.

Run from analysis/:  uv run python projection_backtest.py

Every projection comes from the backend's own code path, so this measures what ships:

- **window**: the old fit, the last 15 games weighted equally (``fit_projection`` defaults);
- **weighted**: ``build_projections(window=82, prior=None)``, recency-weighted, no shrinkage;
- **shipped**: ``build_projections(window=82)``, recency-weighted and shrunk toward the
  typical player built from the data (blocks exempt via the format).

Cutoffs are one and two weeks into each evaluated season (early) and 45/65/85% of the way
through (mid). A player qualifies with 10+ games before the cutoff. Outcomes are per-game
averages over the player's next 15/30/60 games played in the same season, kept when at least
half the horizon was played. Projections use only games before the cutoff.
"""

from datetime import date, timedelta

import numpy as np

import minutes as mn
from ffmodel.contract.db import get_engine
from ffmodel.core.data import get_last_n_games_bulk
from ffmodel.core.model import build_projections, fit_projection
from ffmodel.core.scoring import get_format

FMT = get_format("9cat_h2h")
STATS = list(FMT.base_stats)
IDX = {s: i for i, s in enumerate(STATS)}
COUNTING = ("pts", "reb", "ast", "stl", "blk", "fg3m", "tov")
HORIZONS = (15, 30, 60)
STAR_POINTS = 20


def points(m):
    return 2 * m[..., IDX["fgm"]] + m[..., IDX["fg3m"]] + m[..., IDX["ftm"]]


def stat(m, s):
    return points(m) if s == "pts" else m[..., IDX[s]]


def main(as_of: date = date.today()):
    engine = get_engine()
    logs = mn.load(engine, as_of)
    col = [mn.STATS.index(s) for s in STATS]
    cuts = []
    for k in range(1, len(logs.seasons)):
        sid, start, end, n = logs.seasons[k]
        if n < 1000:
            continue  # the season in progress
        days = np.array(sorted({d for ds in logs.dates.values() for d in ds if start <= d <= end}))
        for kind, qs in (("early", mn.EARLY_QS), ("mid", mn.MID_QS)):
            for q in qs:
                cuts.append((kind, str(days[int(q * (len(days) - 1))]), end))

    obs = {name: [] for name in ("window", "weighted", "shipped")}
    actual = {h: [] for h in HORIZONS}
    attempts = {h: [] for h in HORIZONS}
    kinds = []
    with engine.connect() as conn:
        for kind, cut, end in cuts:
            day = date.fromisoformat(cut) - timedelta(days=1)  # everything before the cutoff
            ids = [
                p for p, d in logs.dates.items() if int(np.searchsorted(d, cut)) >= mn.MIN_GAMES
            ]
            win15 = get_last_n_games_bulk(conn, ids, 15, as_of=day)
            weighted = build_projections(conn, ids, FMT, window=82, as_of=day, prior=None)
            shipped = build_projections(conn, ids, FMT, window=82, as_of=day)
            for pid in ids:
                d = logs.dates[pid]
                after = logs.lines[pid][(d >= cut) & (d <= end)][:, col]
                outs = [after[:h] for h in HORIZONS]
                if len(outs[0]) < HORIZONS[0] / 2:
                    continue
                obs["window"].append(fit_projection(pid, win15[pid], STATS).mean)
                obs["weighted"].append(weighted[pid].mean)
                obs["shipped"].append(shipped[pid].mean)
                for h, g in zip(HORIZONS, outs, strict=True):
                    keep = len(g) >= h / 2
                    actual[h].append(g.mean(0) if keep else np.full(len(STATS), np.nan))
                    attempts[h].append(g.sum(0) if keep else np.full(len(STATS), np.nan))
                kinds.append(kind)

    proj = {k: np.array(v) for k, v in obs.items()}
    act = {h: np.array(v) for h, v in actual.items()}
    att = {h: np.array(v) for h, v in attempts.items()}
    early = np.array(kinds) == "early"
    print(f"player-cutoffs: {len(kinds):,} ({early.sum():,} early-season)")

    def reduction(new, base, h, mask):
        ok = mask & ~np.isnan(act[h][:, 0])
        per = {}
        for s in COUNTING:
            e0 = np.mean((stat(base, s)[ok] - stat(act[h], s)[ok]) ** 2)
            e1 = np.mean((stat(new, s)[ok] - stat(act[h], s)[ok]) ** 2)
            per[s] = 1 - e1 / e0
        return float(np.mean(list(per.values()))), per

    def pct_reduction(new, base, h, made, tried):
        ok = ~np.isnan(act[h][:, 0]) & (att[h][:, IDX[tried]] > 0)
        rate = lambda m: m[ok, IDX[made]] / np.maximum(m[ok, IDX[tried]], 1e-9)
        real = att[h][ok, IDX[made]] / att[h][ok, IDX[tried]]
        w = att[h][ok, IDX[tried]]
        e0 = np.sum(w * (rate(base) - real) ** 2) / w.sum()
        e1 = np.sum(w * (rate(new) - real) ** 2) / w.sum()
        return float(1 - e1 / e0)

    results = []
    everyone = np.ones(len(kinds), bool)
    v, per = reduction(proj["shipped"], proj["window"], 15, everyone)
    results.append(("SC-001 counting stats, next 15, all cutoffs", v, v >= 0.20, "≥ 20%", per))
    for h in (30, 60):
        v, per = reduction(proj["shipped"], proj["window"], h, early)
        results.append((f"SC-002 counting stats, next {h}, early cutoffs", v, v >= 0.20, "≥ 20%", per))
    stars = points(proj["shipped"]) >= STAR_POINTS
    ok = stars & ~np.isnan(act[15][:, 0])
    bias = float(np.mean(points(proj["shipped"])[ok] - points(act[15])[ok]))
    results.append(("SC-003 stars' points bias, next 15, all cutoffs", bias, abs(bias) <= 0.5,
                    "within ±0.5", None))
    for made, tried, label in (("fgm", "fga", "FG%"), ("ftm", "fta", "FT%")):
        v = pct_reduction(proj["shipped"], proj["weighted"], 15, made, tried)
        results.append((f"SC-007 {label} vs unshrunk weighted fit, next 15", v, v >= 0.10,
                        "≥ 10%", None))

    for name, value, passed, threshold, per in results:
        shown = f"{value:+.2f} pts/game" if "bias" in name else f"{100 * value:+.1f}%"
        print(f"{'PASS' if passed else 'FAIL'}  {name}: {shown} (threshold {threshold})")
        if per:
            print("      " + ", ".join(f"{s.upper()} {100 * x:+.1f}%" for s, x in per.items()))
    return all(r[2] for r in results)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
