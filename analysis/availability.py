"""Player availability: games played ÷ games available, and dAB, a backtested model of it.

dAB (Decay-weighted Availability Blend) predicts the share of upcoming games a player plays: a
blend of the recent window and a three-season rate, each shrunk toward the league rate.

Shared by the availability report (availability_analysis.py) and the RGP notebook
(player_rankings_analysis.py), so both use the same fitted model.

Every game, played or missed, is weighted δ^age, where age is how many seasons before the
reference date's season it was played. A season with no games between two seasons with games is
a missed season: it's added as a team's worth of missed games, known from the player's return.
"""

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import polars as pl

WINDOW = 15  # games in the stat window, as in the app
LOOKBACK_SEASONS = 3  # the long-run term's reach
HORIZON = 15  # team games the backtest predicts
AGES = 6  # season ages 0..5; older games pool into age 5
MIN_GAMES, MIN_MINUTES = 10, 20  # backtest eligibility, before the cutoff
EARLY_QS = (0.03, 0.08)  # backtest cutoffs, as fractions of a season's game days
MID_QS = (0.45, 0.65, 0.85)
DELTA_GRID = (0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0)
KAPPA_GRID = tuple(range(0, 201, 5))
KAPPA_W_GRID = (0, 2, 5, 10, 15, 20, 30, 50)

# Platform injury tags → multiplier groups. Judgment: one tag snapshot, no history to fit.
TAG_GROUPS = {
    "IL": "IL / IL+",
    "IL+": "IL / IL+",
    "O": "O",
    "Q": "Q / GTD / DTD",
    "GTD": "Q / GTD / DTD",
    "DTD": "Q / GTD / DTD",
    "SUSP": "SUSP",
    "NA": "NA",
}
DEFAULT_TAG_MULTIPLIERS = {
    "IL / IL+": 0.3,
    "O": 0.6,
    "Q / GTD / DTD": 0.9,
    "SUSP": 0.7,
    "NA": 0.0,
}

_EMPTY = np.array([], dtype="<U10")


@dataclass
class AvailabilityData:
    """Regular-season history up to an as-of date. Dates are ISO strings."""

    seasons: list[tuple[str, str, str, int]]  # (season_id, first day, last day, games)
    played_dates: dict[int, np.ndarray]
    played_minutes: dict[int, np.ndarray]
    team_dates: dict[int, np.ndarray]  # games the player's team(s) played while on the roster
    gap_dates: dict[int, list[tuple[np.ndarray, str]]] = field(default_factory=dict)

    def __post_init__(self):
        self._starts = np.array([s[1] for s in self.seasons])

    @property
    def season_start(self) -> str | None:
        """The latest season's opener."""
        return self.seasons[-1][1] if self.seasons else None

    def season_of(self, dates) -> np.ndarray:
        """Index into `seasons` of each date (-1 before the first season)."""
        return np.searchsorted(self._starts, dates, side="right") - 1

    def counts(
        self,
        pid: int,
        cut: str,
        w: int = WINDOW,
        lookback_seasons: int = LOOKBACK_SEASONS,
        gaps: bool = True,
    ) -> np.ndarray | None:
        """Counts before `cut` by season age: rows are window played, window team games,
        long-run played, long-run team games; columns are ages 0..AGES-1."""
        p = self.played_dates.get(pid, _EMPTY)
        p = p[p < cut]
        t = self.team_dates.get(pid, _EMPTY)
        if gaps:
            known = [d for d, back in self.gap_dates.get(pid, ()) if back < cut]
            if known:
                t = np.sort(np.concatenate([t, *known]))
        t = t[t < cut]
        if not len(p) or not len(t):
            return None
        now = self.season_of(np.array([cut]))[0]

        def ages(d):
            return np.minimum(now - self.season_of(d), AGES - 1)

        def count(d):
            return np.bincount(ages(d), minlength=AGES).astype(float)

        win = p[-w:]
        # Short windows count from the player's first team game, as the app's model does.
        span = t if len(win) < w else t[t >= win[0]]
        return np.stack(
            [
                count(win),
                count(span),
                count(p[ages(p) < lookback_seasons]),
                count(t[ages(t) < lookback_seasons]),
            ]
        )

    def season_line(self, pid: int, k: int) -> tuple[int, int, bool]:
        """(played, team games, missed season?) for player `pid` in season index `k`. A missed
        season's team games are its added missed games."""
        p, t = self.played_dates.get(pid, _EMPTY), self.team_dates.get(pid, _EMPTY)
        for d, _ in self.gap_dates.get(pid, ()):
            if int(self.season_of(d[:1])[0]) == k:
                return 0, len(d), True
        return int((self.season_of(p) == k).sum()), int((self.season_of(t) == k).sum()), False


def load(engine, as_of: date) -> AvailabilityData:
    params = (as_of.isoformat(),)
    with engine.connect() as conn:
        played = conn.exec_driver_sql(
            """SELECT pg.player_id, g.game_date, pg.minutes FROM player_game pg
               JOIN game g USING (game_id)
               WHERE g.season_type = 'regular' AND g.status = 'final' AND g.game_date <= ?
               ORDER BY pg.player_id, g.game_date""",
            params,
        ).all()
        team = conn.exec_driver_sql(
            """SELECT DISTINCT s.player_id, g.game_date, g.game_id FROM game g
               JOIN player_team_stint s ON s.team_id IN (g.home_team_id, g.away_team_id)
                AND g.game_date BETWEEN s.start_date AND COALESCE(s.end_date, '9999-12-31')
               WHERE g.season_type = 'regular' AND g.status = 'final' AND g.game_date <= ?""",
            params,
        ).all()
        seasons = conn.exec_driver_sql(
            """SELECT season_id, MIN(game_date), MAX(game_date), COUNT(*) FROM game
               WHERE season_type = 'regular' AND status = 'final' AND game_date <= ?
               GROUP BY season_id ORDER BY season_id""",
            params,
        ).all()
        days = conn.exec_driver_sql(
            """SELECT DISTINCT season_id, game_date FROM game
               WHERE season_type = 'regular' AND status = 'final' AND game_date <= ?
               ORDER BY game_date""",
            params,
        ).all()
    pf = pl.DataFrame(played, schema=["pid", "d", "min"], orient="row")
    groups = list(pf.group_by("pid", maintain_order=True))
    data = AvailabilityData(
        seasons=[tuple(s) for s in seasons],
        played_dates={k[0]: g["d"].to_numpy() for k, g in groups},
        played_minutes={k[0]: g["min"].to_numpy() for k, g in groups},
        team_dates={
            k[0]: np.sort(g["d"].to_numpy())
            for k, g in pl.DataFrame(team, schema=["pid", "d", "gid"], orient="row").group_by("pid")
        },
    )
    # Missed seasons: a team's worth of evenly spaced game days, known from the player's return.
    season_days: dict[str, list[str]] = {}
    for sid, d in days:
        season_days.setdefault(sid, []).append(d)
    for pid, p in data.played_dates.items():
        played_in = set(data.season_of(p).tolist())
        for k in range(min(played_in) + 1, max(played_in)):
            if k in played_in:
                continue
            sid, _, _, n = data.seasons[k]
            all_days = np.array(season_days[sid])
            per_team = round(2 * n / 30)
            pick = all_days[np.linspace(0, len(all_days) - 1, per_team).round().astype(int)]
            back = p[data.season_of(p) > k][0]
            data.gap_dates.setdefault(pid, []).append((pick, back))
    return data


@dataclass
class Backtest:
    obs: pl.DataFrame  # season, kind (early/mid), cut, pid, actual
    counts: np.ndarray  # (n, 4, AGES), with missed seasons
    counts_model: np.ndarray  # (n, 4, AGES), without: what the app's window sees


def backtest(data: AvailabilityData) -> Backtest:
    """Cutoffs in every completed season that has one before it. Each observation predicts the
    share of the player's next HORIZON team games played (missed seasons count as missed)."""
    cuts = []
    for k in range(1, len(data.seasons)):
        sid, start, end, n = data.seasons[k]
        if n < 1000:
            continue  # the season in progress
        days = np.array(sorted({d for t in data.team_dates.values() for d in t if start <= d <= end}))
        for kind, qs in (("early", EARLY_QS), ("mid", MID_QS)):
            for q in qs:
                cuts.append((sid, kind, str(days[int(q * (len(days) - 1))])))

    rows, counts, counts_model = [], [], []
    for sid, kind, cut in cuts:
        for pid, p in data.played_dates.items():
            before = p < cut
            if before.sum() < MIN_GAMES or data.played_minutes[pid][before].mean() < MIN_MINUTES:
                continue
            future = np.sort(
                np.concatenate(
                    [data.team_dates.get(pid, p[:0]), *[d for d, _ in data.gap_dates.get(pid, ())]]
                )
            )
            nxt = future[future >= cut][:HORIZON]
            if len(nxt) < 10:
                continue
            c = data.counts(pid, cut)
            if c is None:
                continue
            rows.append(
                {"season": sid, "kind": kind, "cut": cut, "pid": pid,
                 "actual": float(np.isin(nxt, p).mean())}
            )
            counts.append(c)
            counts_model.append(data.counts(pid, cut, gaps=False))
    return Backtest(pl.DataFrame(rows), np.array(counts), np.array(counts_model))


def weighted(counts: np.ndarray, delta: float) -> np.ndarray:
    """Collapse the age axis with weights δ^age: (..., 4, AGES) → (..., 4)."""
    return counts @ (delta ** np.arange(AGES))


def shrunk(p, t, k, abar):
    """Rate shrunk toward ā with prior weight k; with no weighted evidence at all, ā itself."""
    den = np.asarray(t + k, dtype=float)
    safe = np.where(den > 0, den, 1.0)
    return np.where(den > 0, (p + k * abar) / safe, abar)


@dataclass
class Fit:
    abar: float
    delta: float
    kappa: float
    kappa_w: float
    b1: float
    b2: float

    def blend(self, counts: np.ndarray | None, delta: float | None = None):
        """(blend, shrunk window, weighted (window p, t, long p, t)) from per-age counts."""
        if counts is None:
            return self.abar, self.abar, np.zeros(4)
        wp, wt, lp, lt = w = weighted(counts, self.delta if delta is None else delta)
        win = float(shrunk(wp, wt, self.kappa_w, self.abar))
        long = float(shrunk(lp, lt, self.kappa, self.abar))
        b = self.abar + self.b1 * (win - self.abar) + self.b2 * (long - self.abar)
        return float(np.clip(b, 0, 1)), win, w


@dataclass
class FitResult:
    fit: Fit
    profile: pl.DataFrame  # δ × cutoff kind → in-sample MSE
    scores: pl.DataFrame  # estimator × cutoff kind → cross-validated MSE
    predictions: pl.DataFrame  # backtest obs + each estimator's prediction


def fit(bt: Backtest) -> FitResult:
    y = bt.obs["actual"].to_numpy()
    season = bt.obs["season"].to_numpy()
    early = (bt.obs["kind"] == "early").to_numpy()
    everyone = np.ones(len(y), bool)
    abar = float(bt.counts[:, 2].sum() / bt.counts[:, 3].sum())

    def mse(pred, mask=everyone):
        return float(np.mean((pred[mask] - y[mask]) ** 2))

    def lsq(X, mask):
        return np.linalg.lstsq(X[mask], (y - abar)[mask], rcond=None)[0]

    def model(delta):
        S = weighted(bt.counts, delta)
        kappa = min(KAPPA_GRID, key=lambda k: mse(shrunk(S[:, 2], S[:, 3], k, abar)))
        long = shrunk(S[:, 2], S[:, 3], kappa, abar)

        def design(kw):
            return np.c_[shrunk(S[:, 0], S[:, 1], kw, abar) - abar, long - abar]

        kw = min(KAPPA_W_GRID, key=lambda k: mse(abar + design(k) @ lsq(design(k), everyone)))
        X = design(kw)
        return {"delta": delta, "kappa": kappa, "kappa_w": kw, "X": X, "b": lsq(X, everyone)}

    models = [model(d) for d in DELTA_GRID]
    profile = []
    for m in models:
        pred = np.clip(abar + m["X"] @ m["b"], 0, 1)
        for label, mask in (("All", everyone), ("Early season", early), ("Mid-season", ~early)):
            profile.append({"δ": m["delta"], "cutoffs": label, "MSE": mse(pred, mask)})
    best = min(models, key=lambda m: mse(abar + m["X"] @ m["b"]))

    def cv(X):
        """Leave-one-season-out predictions."""
        out = np.empty(len(y))
        for s in np.unique(season):
            test = season == s
            out[test] = abar + X[test] @ lsq(X, ~test)
        return np.clip(out, 0, 1)

    Sm = weighted(bt.counts_model, 1.0)
    preds = {
        "League average": np.full(len(y), abar),
        "Window (current model)": np.minimum(1.0, Sm[:, 0] / Sm[:, 1]),
        "dAB, δ = 1": cv(next(m for m in models if m["delta"] == 1.0)["X"]),
        "dAB": cv(best["X"]),
    }
    scores = []
    for name, pred in preds.items():
        row = {"Estimator": name if name != "dAB" else f"dAB, δ = {best['delta']}"}
        for label, mask in (("All", everyone), ("Early season", early), ("Mid-season", ~early)):
            e, base = mse(pred, mask), mse(preds["League average"], mask)
            row[f"{label} MSE"] = round(e, 4)
            row[f"{label} vs. avg"] = f"{100 * (1 - e / base):+.0f}%"
        scores.append(row)
    return FitResult(
        Fit(abar, best["delta"], best["kappa"], best["kappa_w"], float(best["b"][0]),
            float(best["b"][1])),
        pl.DataFrame(profile),
        pl.DataFrame(scores),
        bt.obs.with_columns([pl.Series(name, pred) for name, pred in preds.items()]),
    )


def tag_multiplier(status: str | None, multipliers: dict[str, float] | None = None) -> float:
    group = TAG_GROUPS.get(status or "")
    return (multipliers or DEFAULT_TAG_MULTIPLIERS)[group] if group else 1.0


def cut_after(as_of: date) -> str:
    """The backtest's `cut` for an as-of date: everything through that day counts."""
    return str(np.datetime64(as_of) + np.timedelta64(1, "D"))
