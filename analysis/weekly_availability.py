"""Weekly dAB backtest: does adding last week's playing time improve dAB?

Follows up the weekly projection backtest (docs/weekly-projection-backtest.md, ccsv-rumble #33),
which found that availability is the largest source of weekly error and that zeroing players who
missed all of last week's games helps more than any change to the per-game line.

dAB was fit to the next 15 team games. This script refits it, and variants with a recent term,
for two targets:

- **week**: the share of the player's team games played in the next Mon-Sun week;
- **15 games**: the share of the next 15 team games, dAB's original target.

Cutoffs are every Monday of each completed season after the first (the long-run term needs a
prior season), skipping the All-Star week. The pool matches the availability report: 10+ games
and 20+ minutes a game before the cutoff. Every model is scored leave-one-season-out.

Candidates (each term is a rate minus ā, so 0 means "no information"):

- **shipped**: dAB with its shipped constants, no refit;
- **refit**: dAB's two terms (15-game window, three-season rate), refit to the target;
- **+ last week**: refit plus the share of team games played in the 7 days before the cutoff;
- **+ out**: refit plus a flag for missing every team game in those 7 days;
- **+ recent h**: refit plus a recency-weighted share of the last 20 team games, game j back
  weighted 0.5^(j / h);
- **zero rule**: 0 if out all of last week, else shipped dAB (the projection backtest's rule).

Run (needs the database; see analysis/availability.py):

    cd analysis && uv run python weekly_availability.py

Writes analysis/output/weekly_availability.md and .json.
"""

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np

import availability as av

# dAB's shipped constants (backend/src/ffmodel/core/model/availability.py).
SHIPPED = {"abar": 0.770113, "delta": 0.05, "kappa": 5, "kappa_w": 0, "b1": 0.586418, "b2": 0.144796}
HALF_LIVES = (1, 2, 3, 5, 8)
RECENT_GAMES = 20  # team games the recency-weighted term looks back
OUT = Path(__file__).parent / "output"


@dataclass
class Obs:
    season: np.ndarray  # season id per observation
    counts: np.ndarray  # (n, 4, AGES), dAB's counts
    week_p: np.ndarray  # last week: games played
    week_t: np.ndarray  # last week: team games
    recent: np.ndarray  # (n, RECENT_GAMES): 1 played / 0 missed, most recent first; nan = none
    y_week: np.ndarray  # next week: share played (nan when the team has no game)
    g_week: np.ndarray  # next week: team games
    y_15: np.ndarray  # next 15 team games: share played (nan with fewer than 10)


def mondays(start: str, end: str) -> list[str]:
    d = date.fromisoformat(start)
    d += timedelta(days=(7 - d.weekday()) % 7 or 7)  # the first Monday after opening night
    out, last = [], date.fromisoformat(end)
    while d + timedelta(days=6) <= last:
        out.append(d.isoformat())
        d += timedelta(days=7)
    return out


def build(data: av.AvailabilityData) -> Obs:
    rows = {k: [] for k in Obs.__dataclass_fields__}
    all_team = np.sort(np.concatenate(list(data.team_dates.values())))
    for k in range(1, len(data.seasons)):
        sid, start, end, n = data.seasons[k]
        if n < 1000:
            continue  # the season in progress
        cuts = mondays(start, end)
        # League team games per week; the All-Star week is far below the rest.
        load = {c: int(((all_team >= c) & (all_team < _plus(c, 7))).sum()) for c in cuts}
        typical = np.median(list(load.values()))
        cuts = [c for c in cuts if load[c] >= 0.6 * typical]
        for cut in cuts:
            prev, nxt = _plus(cut, -7), _plus(cut, 7)
            for pid, p in data.played_dates.items():
                before = p < cut
                if before.sum() < av.MIN_GAMES or data.played_minutes[pid][before].mean() < av.MIN_MINUTES:
                    continue
                c = data.counts(pid, cut)
                if c is None:
                    continue
                t = data.team_dates.get(pid, p[:0])
                gaps = [d for d, _ in data.gap_dates.get(pid, ())]
                future = np.sort(np.concatenate([t, *gaps]))
                wk = future[(future >= cut) & (future < nxt)]
                f15 = future[future >= cut][: av.HORIZON]
                if not len(wk) and len(f15) < 10:
                    continue
                last = t[(t >= prev) & (t < cut)]
                back = t[t < cut][-RECENT_GAMES:][::-1]
                rec = np.full(RECENT_GAMES, np.nan)
                rec[: len(back)] = np.isin(back, p)
                rows["season"].append(sid)
                rows["counts"].append(c)
                rows["week_p"].append(int(np.isin(last, p).sum()))
                rows["week_t"].append(len(last))
                rows["recent"].append(rec)
                rows["y_week"].append(float(np.isin(wk, p).mean()) if len(wk) else np.nan)
                rows["g_week"].append(len(wk))
                rows["y_15"].append(float(np.isin(f15, p).mean()) if len(f15) >= 10 else np.nan)
    return Obs(**{k: np.array(v) for k, v in rows.items()})


def _plus(d: str, days: int) -> str:
    return (date.fromisoformat(d) + timedelta(days=days)).isoformat()


def base_terms(obs: Obs, abar: float) -> tuple[np.ndarray, np.ndarray]:
    """dAB's window and long-run terms at the shipped δ, κ, κ_w, each minus ā."""
    wp, wt, lp, lt = np.moveaxis(av.weighted(obs.counts, SHIPPED["delta"]), -1, 0)
    win = av.shrunk(wp, wt, SHIPPED["kappa_w"], abar)
    long = av.shrunk(lp, lt, SHIPPED["kappa"], abar)
    return win - abar, long - abar


def last_week_term(obs: Obs, abar: float) -> np.ndarray:
    """Share of last week's team games played, minus ā; 0 when the team didn't play."""
    t = obs.week_t.astype(float)
    return np.where(t > 0, obs.week_p / np.where(t > 0, t, 1) - abar, 0.0)


def out_flag(obs: Obs) -> np.ndarray:
    return ((obs.week_t > 0) & (obs.week_p == 0)).astype(float)


def recent_term(obs: Obs, h: float, abar: float) -> np.ndarray:
    w = 0.5 ** (np.arange(RECENT_GAMES) / h)
    have = ~np.isnan(obs.recent)
    num = (np.nan_to_num(obs.recent) * w).sum(1)
    den = (have * w).sum(1)
    return np.where(den > 0, num / np.where(den > 0, den, 1) - abar, 0.0)


def shipped_pred(obs: Obs) -> np.ndarray:
    win, long = base_terms(obs, SHIPPED["abar"])
    return np.clip(SHIPPED["abar"] + SHIPPED["b1"] * win + SHIPPED["b2"] * long, 0, 1)


def cv_fit(X: np.ndarray, y: np.ndarray, season: np.ndarray, abar: float, weight=None):
    """Leave-one-season-out predictions and the coefficients fit on every season."""
    ok = ~np.isnan(y)
    sw = np.sqrt(weight) if weight is not None else np.ones(len(y))

    def lsq(mask):
        return np.linalg.lstsq(X[mask] * sw[mask, None], (y[mask] - abar) * sw[mask], rcond=None)[0]

    out = np.full(len(y), np.nan)
    for s in np.unique(season[ok]):
        test = ok & (season == s)
        out[test] = abar + X[test] @ lsq(ok & (season != s))
    return np.clip(out, 0, 1), lsq(ok)


def score(pred, y, g=None, mask=None) -> dict:
    ok = ~np.isnan(y) & ~np.isnan(pred)
    if mask is not None:
        ok &= mask
    e = pred[ok] - y[ok]
    row = {"n": int(ok.sum()), "MSE": float(np.mean(e**2)), "bias": float(np.mean(e))}
    if g is not None:  # error in games played this week, per player-week
        gg = g[ok]
        row["MSE (games)"] = float(np.mean((e * gg) ** 2))
        row["bias (games)"] = float(np.mean(e * gg))
    return row


def run(obs: Obs) -> dict:
    results = {}
    for target, y, g in (("week", obs.y_week, obs.g_week), ("15 games", obs.y_15, None)):
        ok = ~np.isnan(y)
        abar = float(np.mean(y[ok]))  # each target's own league rate
        win, long = base_terms(obs, abar)
        base = np.c_[win, long]
        cands = {
            "refit": base,
            "+ last week": np.c_[base, last_week_term(obs, abar)],
            "+ out": np.c_[base, out_flag(obs)],
            "+ last week + out": np.c_[base, last_week_term(obs, abar), out_flag(obs)],
        }
        for h in HALF_LIVES:
            cands[f"+ recent h={h}"] = np.c_[base, recent_term(obs, h, abar)]
        preds, coefs = {"shipped": shipped_pred(obs)}, {}
        zero = np.where(out_flag(obs) > 0, 0.0, preds["shipped"])
        preds["zero rule"] = zero
        weight = g.astype(float) if g is not None else None
        for name, X in cands.items():
            preds[name], coefs[name] = cv_fit(X, y, obs.season, abar, weight)
        out_mask = out_flag(obs) > 0
        results[target] = {
            "abar": abar,
            "scores": {
                name: {
                    "all": score(p, y, g),
                    "out last week": score(p, y, g, out_mask),
                    "played last week": score(p, y, g, ~out_mask),
                    "per season": {
                        s: score(p, y, g, obs.season == s) for s in np.unique(obs.season[ok])
                    },
                }
                for name, p in preds.items()
            },
            "coefficients": {k: [float(x) for x in v] for k, v in coefs.items()},
        }
    return results


def report(res: dict, obs: Obs) -> str:
    out_n = int(out_flag(obs).sum())
    lines = [
        "# Weekly dAB backtest",
        "",
        f"{len(obs.season):,} player-Mondays over seasons {', '.join(np.unique(obs.season))}; "
        f"{out_n:,} of them missed every team game the week before.",
        "",
    ]
    for target, r in res.items():
        lines += [f"## Target: {target} (ā = {r['abar']:.3f})", ""]
        cols = ["MSE", "bias"] + (["MSE (games)", "bias (games)"] if target == "week" else [])
        lines.append("| Model | " + " | ".join(cols) + " | Out last week: MSE | bias | Played: MSE |")
        lines.append("|---" * (len(cols) + 4) + "|")
        base = r["scores"]["shipped"]["all"]["MSE"]
        for name, s in r["scores"].items():
            a, o, pl_ = s["all"], s["out last week"], s["played last week"]
            cells = [f"{a[c]:.4f}" if "MSE" in c else f"{a[c]:+.3f}" for c in cols]
            cells[0] += f" ({100 * (1 - a['MSE'] / base):+.1f}%)"
            lines.append(
                f"| {name} | " + " | ".join(cells)
                + f" | {o['MSE']:.4f} | {o['bias']:+.3f} | {pl_['MSE']:.4f} |"
            )
        lines += ["", "Per season MSE:", ""]
        seasons = list(next(iter(r["scores"].values()))["per season"])
        lines.append("| Model | " + " | ".join(seasons) + " |")
        lines.append("|---" * (len(seasons) + 1) + "|")
        for name, s in r["scores"].items():
            lines.append(
                f"| {name} | " + " | ".join(f"{s['per season'][x]['MSE']:.4f}" for x in seasons) + " |"
            )
        lines += ["", "Coefficients (fit on all seasons; terms are rates minus ā):", ""]
        for name, c in r["coefficients"].items():
            lines.append(f"- {name}: " + ", ".join(f"{x:.4f}" for x in c))
        lines.append("")
    return "\n".join(lines)


def main():
    from ffmodel.contract.db import get_engine

    data = av.load(get_engine(), date.today())
    obs = build(data)
    res = run(obs)
    OUT.mkdir(exist_ok=True)
    md = report(res, obs)
    (OUT / "weekly_availability.md").write_text(md)
    (OUT / "weekly_availability.json").write_text(json.dumps(res, indent=1))
    print(md)


if __name__ == "__main__":
    main()
