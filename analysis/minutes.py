"""Minutes trend multiplier: scale a window projection by where a player's minutes are heading.

A projection averages the last WINDOW games played, so a player whose role changed (a starter
benched by new signings, a reserve promoted) is projected on the old role. The multiplier is

    m = forecast minutes / window minutes,   forecast = W + beta * (R - W)

where W is the window's mean minutes and R a recency-weighted mean (each game weighs
0.5^(games ago / half-life), and games from before the current season also weigh `delta`).
m scales counting stats; percentages and per-minute production are unchanged. It covers minutes
when playing: games missed are availability's job (dAB).
"""

import warnings
from dataclasses import dataclass
from datetime import date

import numpy as np
import polars as pl

WINDOW = 15  # games in the stat window, as in the app
RECENT = 30  # games the recency-weighted mean can reach back
HORIZON = 15  # games played the backtest predicts
MIN_GAMES = 10  # backtest eligibility: games before the cutoff
MIN_NEXT = 5  # ... and games played after it
EARLY_QS = (0.03, 0.08)
MID_QS = (0.45, 0.65, 0.85)
HALF_LIFE_GRID = (1, 2, 3, 5, 8, 12, 20)
DELTA_GRID = (0.0, 0.05, 0.1, 0.25, 0.5, 1.0)
CLIP = (0.25, 2.0)  # multiplier bounds

STATS = ("minutes", "pts", "reb", "ast", "stl", "blk", "fg3m", "tov", "fgm", "fga", "ftm", "fta")
COUNTING = ("pts", "reb", "ast", "stl", "blk", "fg3m", "tov")


@dataclass
class GameLogs:
    seasons: list[tuple[str, str, str, int]]  # (season_id, first day, last day, games)
    dates: dict[int, np.ndarray]  # per player, ascending ISO dates of games played
    lines: dict[int, np.ndarray]  # per player, (games, len(STATS)) box-score lines

    def __post_init__(self):
        self._starts = np.array([s[1] for s in self.seasons])

    def season_of(self, dates) -> np.ndarray:
        return np.searchsorted(self._starts, dates, side="right") - 1

    def before(self, pid: int, cut: str, n: int):
        """The last `n` games before `cut`, most recent first: (lines, from an earlier season?)."""
        d = self.dates.get(pid)
        if d is None:
            return None
        k = int(np.searchsorted(d, cut))
        if k == 0:
            return None
        lo = max(0, k - n)
        idx = np.arange(k - 1, lo - 1, -1)
        now = self.season_of(np.array([cut]))[0]
        return self.lines[pid][idx], self.season_of(d[idx]) < now

    def after(self, pid: int, cut: str, n: int) -> np.ndarray | None:
        d = self.dates.get(pid)
        if d is None:
            return None
        k = int(np.searchsorted(d, cut))
        return self.lines[pid][k : k + n]


def load(engine, as_of: date) -> GameLogs:
    cols = ", ".join(f"pg.{s}" for s in STATS)
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(
            f"""SELECT pg.player_id, g.game_date, {cols} FROM player_game pg
                JOIN game g USING (game_id)
                WHERE g.season_type = 'regular' AND g.status = 'final' AND g.game_date <= ?
                ORDER BY pg.player_id, g.game_date""",
            (as_of.isoformat(),),
        ).all()
        seasons = conn.exec_driver_sql(
            """SELECT season_id, MIN(game_date), MAX(game_date), COUNT(*) FROM game
               WHERE season_type = 'regular' AND status = 'final' AND game_date <= ?
               GROUP BY season_id ORDER BY season_id""",
            (as_of.isoformat(),),
        ).all()
    df = pl.DataFrame(rows, schema=["pid", "d", *STATS], orient="row")
    dates, lines = {}, {}
    for (pid,), g in df.group_by("pid", maintain_order=True):
        dates[pid] = g["d"].to_numpy()
        lines[pid] = g.select(STATS).to_numpy().astype(float)
    return GameLogs([tuple(s) for s in seasons], dates, lines)


@dataclass
class Features:
    """Per observation: the last RECENT games' minutes (most recent first, NaN-padded), whether
    each is from an earlier season, and the window's mean line."""

    minutes: np.ndarray  # (n, RECENT)
    earlier: np.ndarray  # (n, RECENT) bool
    window: np.ndarray  # (n, len(STATS)) mean of the last WINDOW games
    poss: np.ndarray  # (n, RECENT) possessions used per game: FGA + 0.44 FTA + TOV


def features(logs: GameLogs, pairs) -> Features:
    n = len(pairs)
    mins = np.full((n, RECENT), np.nan)
    earlier = np.zeros((n, RECENT), bool)
    window = np.zeros((n, len(STATS)))
    poss = np.full((n, RECENT), np.nan)
    fga, fta, tov = STATS.index("fga"), STATS.index("fta"), STATS.index("tov")
    for i, (pid, cut) in enumerate(pairs):
        lines, prev = logs.before(pid, cut, RECENT)
        mins[i, : len(lines)] = lines[:, 0]
        earlier[i, : len(lines)] = prev
        window[i] = lines[:WINDOW].mean(axis=0)
        poss[i, : len(lines)] = lines[:, fga] + 0.44 * lines[:, fta] + lines[:, tov]
    return Features(mins, earlier, window, poss)


def recent_mean(f: Features, half_life: float, delta: float) -> np.ndarray:
    """Recency-weighted mean minutes. With no weight at all (δ = 0 and no games this season),
    the window's mean: there's no evidence of a trend."""
    w = 0.5 ** (np.arange(RECENT) / half_life) * np.where(f.earlier, delta, 1.0)
    w = np.where(np.isnan(f.minutes), 0.0, w)
    total = w.sum(axis=1)
    weighted = np.nansum(np.nan_to_num(f.minutes) * w, axis=1)
    return np.where(total > 0, weighted / np.where(total > 0, total, 1), f.window[:, 0])


@dataclass
class Model:
    half_life: float
    delta: float
    beta: float

    def forecast(self, f: Features) -> np.ndarray:
        W = f.window[:, 0]
        return np.maximum(W + self.beta * (recent_mean(f, self.half_life, self.delta) - W), 0)

    def multiplier(self, f: Features) -> np.ndarray:
        W = f.window[:, 0]
        m = np.where(W > 0, self.forecast(f) / np.where(W > 0, W, 1), 1.0)
        return np.clip(m, *CLIP)


@dataclass
class Backtest:
    obs: pl.DataFrame  # season, kind, cut, pid
    f: Features
    next_line: np.ndarray  # (n, len(STATS)) mean over the next HORIZON games played
    next_minutes: np.ndarray  # (n, HORIZON) minutes in each of those games, NaN-padded
    next_poss: np.ndarray  # (n, HORIZON) possessions used in each


def backtest(logs: GameLogs) -> Backtest:
    cuts = []
    for k in range(1, len(logs.seasons)):
        sid, start, end, n = logs.seasons[k]
        if n < 1000:
            continue  # the season in progress
        days = np.array(sorted({d for ds in logs.dates.values() for d in ds if start <= d <= end}))
        for kind, qs in (("early", EARLY_QS), ("mid", MID_QS)):
            for q in qs:
                cuts.append((sid, kind, str(days[int(q * (len(days) - 1))])))
    rows, pairs, nxt, nxt_min, nxt_poss = [], [], [], [], []
    fga, fta, tov = STATS.index("fga"), STATS.index("fta"), STATS.index("tov")
    for sid, kind, cut in cuts:
        for pid, d in logs.dates.items():
            k = int(np.searchsorted(d, cut))
            if k < MIN_GAMES:
                continue
            after = logs.after(pid, cut, HORIZON)
            if after is None or len(after) < MIN_NEXT:
                continue
            rows.append({"season": sid, "kind": kind, "cut": cut, "pid": pid})
            pairs.append((pid, cut))
            nxt.append(after.mean(axis=0))
            pad = np.full(HORIZON - len(after), np.nan)
            nxt_min.append(np.r_[after[:, 0], pad])
            nxt_poss.append(np.r_[after[:, fga] + 0.44 * after[:, fta] + after[:, tov], pad])
    return Backtest(pl.DataFrame(rows), features(logs, pairs), np.array(nxt), np.array(nxt_min),
                    np.array(nxt_poss))


@dataclass
class FitResult:
    model: Model
    grid: pl.DataFrame  # half-life × δ → in-sample MSE of the minutes forecast
    scores: pl.DataFrame  # forecast × cutoff kind → cross-validated minutes MSE
    stat_scores: pl.DataFrame  # stat → error reduction from the multiplier
    predictions: pl.DataFrame  # backtest obs + forecasts and actuals


def _beta(x, y, mask):
    return float(np.sum(x[mask] * y[mask]) / np.sum(x[mask] ** 2)) if np.any(x[mask]) else 0.0


def fit(bt: Backtest) -> FitResult:
    f, y = bt.f, bt.next_line[:, 0]
    W = f.window[:, 0]
    season = bt.obs["season"].to_numpy()
    early = (bt.obs["kind"] == "early").to_numpy()
    everyone = np.ones(len(y), bool)

    def mse(pred, mask=everyone):
        return float(np.mean((pred[mask] - y[mask]) ** 2))

    grid = []
    for h in HALF_LIFE_GRID:
        for d in DELTA_GRID:
            x = recent_mean(f, h, d) - W
            grid.append({"half-life": h, "δ": d, "β": _beta(x, y - W, everyone),
                         "MSE": mse(W + _beta(x, y - W, everyone) * x)})
    grid_df = pl.DataFrame(grid)
    best = grid_df.sort("MSE").row(0, named=True)
    x = recent_mean(f, best["half-life"], best["δ"]) - W

    def cv(signal):
        out = np.empty(len(y))
        for s in np.unique(season):
            test = season == s
            out[test] = W[test] + _beta(signal, y - W, ~test) * signal[test]
        return np.maximum(out, 0)

    # A naive trend: the least-squares line through the window's minutes, extended to the
    # middle of the next HORIZON games.
    m15 = f.minutes[:, :WINDOW]
    t = -np.arange(WINDOW, dtype=float)  # 0 = most recent
    ok = ~np.isnan(m15)
    tm = np.where(ok, t, np.nan)
    slope = np.nansum((tm - np.nanmean(tm, 1, keepdims=True)) * (m15 - W[:, None]), 1) / np.maximum(
        np.nansum((tm - np.nanmean(tm, 1, keepdims=True)) ** 2, 1), 1e-9
    )
    line_now = W - slope * np.nanmean(tm, 1)
    trend = np.maximum(line_now + slope * (HORIZON + 1) / 2, 0)
    last5 = np.nanmean(f.minutes[:, :5], axis=1)

    preds = {
        "Window average (no multiplier)": W,
        "Last 5 games": last5,
        "Linear trend through the window": trend,
        "Trend model (CV)": cv(x),
    }
    scores = []
    for name, p in preds.items():
        row = {"Forecast": name}
        for label, mask in (("All", everyone), ("Early season", early), ("Mid-season", ~early)):
            e, base = mse(p, mask), mse(W, mask)
            row[f"{label} MSE"] = round(e, 1)
            row[f"{label} vs. window"] = f"{100 * (1 - e / base):+.0f}%"
        scores.append(row)

    model = Model(best["half-life"], best["δ"], best["β"])
    mult = np.clip(np.where(W > 0, preds["Trend model (CV)"] / np.where(W > 0, W, 1), 1), *CLIP)
    stat_rows = []
    for s in COUNTING:
        i = STATS.index(s)
        actual, base = bt.next_line[:, i], f.window[:, i]
        row = {"Stat": s.upper()}
        for label, mask in (("All", everyone), ("Early season", early), ("Mid-season", ~early)):
            e0 = np.mean((base[mask] - actual[mask]) ** 2)
            e1 = np.mean((base[mask] * mult[mask] - actual[mask]) ** 2)
            row[label] = f"{100 * (1 - e1 / e0):+.0f}%"
        stat_rows.append(row)

    out = bt.obs.with_columns(
        pl.Series("window", W),
        pl.Series("forecast", preds["Trend model (CV)"]),
        pl.Series("multiplier", mult),
        pl.Series("actual", y),
    )
    return FitResult(model, grid_df, pl.DataFrame(scores), pl.DataFrame(stat_rows), out)


def cut_after(as_of: date) -> str:
    return str(np.datetime64(as_of) + np.timedelta64(1, "D"))


# --- Roles: do minutes cluster, and does a role shift predict minutes? --------------------------
ROLE_K_GRID = (2, 3, 4, 5)
ROLE_RECENT = 5  # games that update the role (the rest of the window sets the prior)
ROLE_BINS = np.arange(0, 52, 3)  # single-game minutes histogram for each role's likelihood
USAGE_BINS = np.arange(0, 1.31, 0.1)  # single-game usage histogram (games of 5+ minutes)
USAGE_MIN_MINUTES = 5
ROLE_FEATURES = ("Mean minutes", "Game-to-game spread", "Usage per minute")
# Names for fewer than five roles, by mean minutes; a far higher-spread role becomes "Platoon".
ROLE_NAMES = {2: ("Bench", "Starter"), 3: ("Bench", "Role player", "Starter"),
              4: ("Bench", "Role player", "Starter", "Star")}
PLATOON_SPREAD = 1.4  # a role this many times the others' median SD is named "Platoon"


def role_features(minutes: np.ndarray, poss: np.ndarray) -> np.ndarray:
    """Per row: mean minutes, game-to-game spread, and usage (possessions used per minute),
    ignoring NaN padding. Spread is the interquartile range ÷ 1.349 (an SD for normal data) so
    one short game, an injury exit, say, doesn't move a starter into a volatile role. A row with
    no games gives NaN, which callers treat as "no evidence"."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        total = np.nansum(minutes, 1)
        usage = np.where(total > 0, np.nansum(poss, 1) / np.where(total > 0, total, 1), np.nan)
        usage = np.where(np.isnan(minutes).all(1), np.nan, usage)
        q75, q25 = np.nanpercentile(minutes, 75, axis=1), np.nanpercentile(minutes, 25, axis=1)
        return np.c_[np.nanmean(minutes, 1), (q75 - q25) / 1.349, usage]


def _game_usage(minutes: np.ndarray, poss: np.ndarray):
    """Single-game usage and whether it's usable (5+ minutes)."""
    ok = ~np.isnan(minutes) & (minutes >= USAGE_MIN_MINUTES)
    return np.where(ok, poss / np.where(ok, minutes, 1), 0.0), ok


def role_names(X: np.ndarray, lab: np.ndarray, k: int) -> tuple[str, ...]:
    """Names from each role's profile (roles are indexed by mean minutes). With five roles:
    star has the most minutes and usage combined, bench the fewest minutes, platoon the
    widest spread; of the last two, the higher-usage one is the starter, the other the role
    player. With fewer roles: by mean minutes, and a middle role with far higher spread than
    the others is the platoon."""
    prof = np.array([X[lab == c].mean(0) for c in range(k)])
    if k == 5:
        z = (prof - prof.mean(0)) / prof.std(0)
        names = [""] * k
        left = list(range(k))

        def take(i, name):
            names[i] = name
            left.remove(i)

        take(max(left, key=lambda i: z[i, 0] + z[i, 2]), "Star")
        take(min(left, key=lambda i: prof[i, 0]), "Bench")
        take(max(left, key=lambda i: prof[i, 1]), "Platoon")
        take(max(left, key=lambda i: prof[i, 2]), "Starter")
        take(left[0], "Role player")
        return tuple(names)
    names = list(ROLE_NAMES[k])
    if k >= 3:
        middle = range(1, k - 1)  # the fewest- and most-minutes roles keep their names
        top = max(middle, key=lambda i: prof[i, 1])
        if prof[top, 1] >= PLATOON_SPREAD * np.median(np.delete(prof[:, 1], top)):
            names[top] = "Platoon"
    return tuple(names)


@dataclass
class RoleModel:
    """Roles as a Gaussian mixture over a window's minutes (mean, SD) and usage, indexed by
    mean minutes."""

    k: int
    center: np.ndarray
    scale: np.ndarray
    gmm: object
    order: np.ndarray  # mixture component → role index (by mean minutes)
    loglik: np.ndarray  # (k, bins) log-probability of a single game's minutes in each role
    loglik_usage: np.ndarray  # (k, usage bins) the same for a single game's usage
    next_minutes: np.ndarray  # (k,) mean minutes over the next HORIZON games, by window role
    names: tuple[str, ...]  # from each role's profile (role_names)

    def _proba(self, X):
        p = self.gmm.predict_proba((X - self.center) / self.scale)
        out = np.empty_like(p)
        out[:, self.order] = p
        return out

    def label(self, minutes: np.ndarray, poss: np.ndarray) -> np.ndarray:
        return self._proba(role_features(minutes, poss)).argmax(1)

    def posterior(self, f: "Features", delta: float) -> np.ndarray:
        """Role probabilities: the window's older games set the prior, and the last ROLE_RECENT
        games' minutes and usage update it (games from an earlier season count δ)."""
        n = len(f.minutes)
        older = role_features(f.minutes[:, ROLE_RECENT:WINDOW], f.poss[:, ROLE_RECENT:WINDOW])
        prior = np.full((n, self.k), 1.0 / self.k)
        ok = ~np.isnan(older).any(1)
        if ok.any():
            prior[ok] = self._proba(older[ok])
        logp = np.log(np.maximum(prior, 1e-9))
        rec = f.minutes[:, :ROLE_RECENT]
        w = np.where(f.earlier[:, :ROLE_RECENT], delta, 1.0)
        idx = np.clip(np.digitize(np.nan_to_num(rec), ROLE_BINS) - 1, 0, len(ROLE_BINS) - 2)
        u, u_ok = _game_usage(rec, f.poss[:, :ROLE_RECENT])
        u_idx = np.clip(np.digitize(u, USAGE_BINS) - 1, 0, len(USAGE_BINS) - 2)
        for c in range(self.k):
            logp[:, c] += np.where(np.isnan(rec), 0.0, w * self.loglik[c][idx]).sum(1)
            logp[:, c] += np.where(u_ok, w * self.loglik_usage[c][u_idx], 0.0).sum(1)
        post = np.exp(logp - logp.max(1, keepdims=True))
        return post / post.sum(1, keepdims=True)

    def forecast(self, f: "Features", delta: float) -> np.ndarray:
        return self.posterior(f, delta) @ self.next_minutes


def fit_roles_model(f: "Features", next_minutes: np.ndarray, k: int, mask=None) -> RoleModel:
    from sklearn.mixture import GaussianMixture

    mask = np.ones(len(next_minutes), bool) if mask is None else mask
    X = role_features(f.minutes[mask, :WINDOW], f.poss[mask, :WINDOW])
    center, scale = X.mean(0), X.std(0)
    gmm = GaussianMixture(k, covariance_type="full", random_state=0, n_init=3).fit(
        (X - center) / scale
    )
    raw = gmm.predict((X - center) / scale)
    order = np.empty(k, int)
    order[np.argsort([X[raw == c, 0].mean() for c in range(k)])] = np.arange(k)
    lab = order[raw]
    loglik, loglik_usage = [], []
    for c in range(k):
        mins = f.minutes[mask][lab == c, :WINDOW]
        games = mins.ravel()[~np.isnan(mins.ravel())]
        h = np.histogram(np.clip(games, 0, ROLE_BINS[-1] - 0.1), bins=ROLE_BINS)[0] + 1.0
        loglik.append(np.log(h / h.sum()))
        u, ok = _game_usage(mins, f.poss[mask][lab == c, :WINDOW])
        h = np.histogram(np.clip(u[ok], 0, USAGE_BINS[-1] - 1e-3), bins=USAGE_BINS)[0] + 1.0
        loglik_usage.append(np.log(h / h.sum()))
    nxt = np.array([next_minutes[mask][lab == c].mean() for c in range(k)])
    return RoleModel(k, center, scale, gmm, order, np.array(loglik), np.array(loglik_usage), nxt,
                     role_names(X, lab, k))


@dataclass
class Combined:
    """forecast = W + β_trend (R − W) + β_role (role forecast − W)."""

    trend: Model
    roles: RoleModel
    beta_trend: float
    beta_role: float

    def forecast(self, f: "Features") -> np.ndarray:
        W = f.window[:, 0]
        x_t = recent_mean(f, self.trend.half_life, self.trend.delta) - W
        x_r = self.roles.forecast(f, self.trend.delta) - W
        return np.maximum(W + self.beta_trend * x_t + self.beta_role * x_r, 0)

    def multiplier(self, f: "Features") -> np.ndarray:
        W = f.window[:, 0]
        return np.clip(np.where(W > 0, self.forecast(f) / np.where(W > 0, W, 1), 1.0), *CLIP)


@dataclass
class RoleResult:
    model: Combined
    selection: pl.DataFrame  # k → BIC, silhouette, CV MSE of trend + role
    profiles: pl.DataFrame  # role → size, minutes mean/SD, next minutes
    spread: pl.DataFrame  # SD of single-game minutes within bands of mean minutes
    bimodality: dict[str, float]  # band → bimodality coefficient of SD
    scores: pl.DataFrame  # forecast × cutoff kind → CV minutes MSE
    stat_scores: pl.DataFrame
    shifts: pl.DataFrame  # season → flagged shifts and where the next 15 games landed
    components: pl.DataFrame  # which part of the role signal predicts: level, drift, both
    bias: pl.DataFrame  # mean forecast error by window minutes, trend vs. trend + role
    predictions: pl.DataFrame


def fit_roles(bt: Backtest, trend: FitResult, k: int | None = None) -> RoleResult:
    """`k` roles; by default the fewest within 0.1 MSE of the best cross-validated count."""
    from scipy.stats import kurtosis, skew
    from sklearn.metrics import silhouette_score

    f, y = bt.f, bt.next_line[:, 0]
    W = f.window[:, 0]
    season = bt.obs["season"].to_numpy()
    early = (bt.obs["kind"] == "early").to_numpy()
    everyone = np.ones(len(y), bool)
    tm = trend.model
    x_t = recent_mean(f, tm.half_life, tm.delta) - W
    X = role_features(f.minutes[:, :WINDOW], f.poss[:, :WINDOW])

    def mse(p, mask=everyone):
        return float(np.mean((p[mask] - y[mask]) ** 2))

    def cv(k):
        """Leave-one-season-out: roles and weights fit on the other seasons."""
        out, role_only, shifts = np.empty(len(y)), np.empty(len(y)), []
        for s in np.unique(season):
            test = season == s
            rm = fit_roles_model(f, y, k, ~test)
            x_r = rm.forecast(f, tm.delta) - W
            A = np.c_[x_t, x_r]
            b = np.linalg.lstsq(A[~test], (y - W)[~test], rcond=None)[0]
            out[test] = W[test] + A[test] @ b
            br = np.linalg.lstsq(x_r[~test, None], (y - W)[~test], rcond=None)[0]
            role_only[test] = W[test] + x_r[test] * br[0]
            post = rm.posterior(f, tm.delta)[test].argmax(1)
            window_role = rm.label(f.minutes[test, :WINDOW], f.poss[test, :WINDOW])
            next_role = rm.label(bt.next_minutes[test], bt.next_poss[test])
            flagged = post != window_role
            shifts.append({
                "Season": s,
                "Player-cutoffs": int(test.sum()),
                "Shifts flagged": int(flagged.sum()),
                "Next 15 match new role": f"{np.mean(next_role[flagged] == post[flagged]):.0%}",
                "Next 15 match old role": f"{np.mean(next_role[flagged] == window_role[flagged]):.0%}",
            })
        return np.maximum(out, 0), np.maximum(role_only, 0), shifts

    sub = np.random.default_rng(0).choice(len(X), min(3000, len(X)), replace=False)
    selection, runs = [], {}
    for kk in ROLE_K_GRID:
        rm = fit_roles_model(f, y, kk)
        Z = (X - rm.center) / rm.scale
        runs[kk] = cv(kk)
        selection.append({
            "Roles (k)": kk,
            "BIC": round(float(rm.gmm.bic(Z))),
            "Silhouette": round(float(silhouette_score(Z[sub], rm.gmm.predict(Z)[sub])), 3),
            "CV MSE, trend + role": round(mse(runs[kk][0]), 2),
        })
    sel = pl.DataFrame(selection)
    if k is None:
        best_mse = sel["CV MSE, trend + role"].min()
        k = int(sel.filter(pl.col("CV MSE, trend + role") <= best_mse + 0.1)["Roles (k)"].min())
    combined_cv, role_cv, shifts = runs[k]

    # Which part of the role signal predicts? Level: the posterior role's typical minutes.
    # Drift: only the change between the window's role and the posterior role.
    comp = {"Trend only": trend.predictions["forecast"].to_numpy()}
    for variant in ("Trend + role level", "Trend + role drift", "Trend + level + drift"):
        out = np.empty(len(y))
        for s in np.unique(season):
            test = season == s
            rm = fit_roles_model(f, y, k, ~test)
            post = rm.posterior(f, tm.delta)
            p_window = rm._proba(X)
            level, drift = post @ rm.next_minutes - W, (post - p_window) @ rm.next_minutes
            A = {"Trend + role level": np.c_[x_t, level], "Trend + role drift": np.c_[x_t, drift],
                 "Trend + level + drift": np.c_[x_t, level, drift]}[variant]
            out[test] = W[test] + A[test] @ np.linalg.lstsq(A[~test], (y - W)[~test], rcond=None)[0]
        comp[variant] = out
    components = pl.DataFrame([
        {"Forecast": n, "CV MSE": round(mse(p), 2),
         "vs. window": f"{100 * (1 - mse(p) / mse(W)):+.0f}%",
         "Early season vs. window": f"{100 * (1 - mse(p, early) / mse(W, early)):+.0f}%"}
        for n, p in comp.items()
    ])
    bias = pl.DataFrame([
        {"Window minutes": f"{lo}–{hi}", "Player-cutoffs": int(((W >= lo) & (W < hi)).sum()),
         "Trend only": round(float(np.mean((comp["Trend only"] - y)[(W >= lo) & (W < hi)])), 2),
         "Trend + role": round(float(np.mean((combined_cv - y)[(W >= lo) & (W < hi)])), 2)}
        for lo, hi in ((0, 12), (12, 20), (20, 28), (28, 33), (33, 48))
    ])

    roles = fit_roles_model(f, y, k)
    x_r = roles.forecast(f, tm.delta) - W
    b = np.linalg.lstsq(np.c_[x_t, x_r], y - W, rcond=None)[0]
    model = Combined(tm, roles, float(b[0]), float(b[1]))

    lab = roles.label(f.minutes[:, :WINDOW], f.poss[:, :WINDOW])
    pts = f.window[:, STATS.index("pts")]
    profiles = pl.DataFrame([
        {"Role": roles.names[c], "Share": f"{np.mean(lab == c):.0%}",
         "Mean minutes": round(float(X[lab == c, 0].mean()), 1),
         "Game-to-game spread": round(float(X[lab == c, 1].mean()), 1),
         "Usage per minute": round(float(X[lab == c, 2].mean()), 3),
         "Points": round(float(pts[lab == c].mean()), 1),
         "Next 15 games' minutes": round(float(roles.next_minutes[c]), 1)}
        for c in range(k)
    ])
    spread, bimod = [], {}
    for lo, hi in ((0, 12), (12, 20), (20, 28), (28, 48)):
        sd = X[(X[:, 0] >= lo) & (X[:, 0] < hi), 1]
        n = len(sd)
        spread.append({"Mean minutes": f"{lo}–{hi}", "Players": n,
                       "Median spread": round(float(np.median(sd)), 1),
                       "Spread 10th–90th pct":
                           f"{np.percentile(sd, 10):.1f}–{np.percentile(sd, 90):.1f}"})
        bimod[f"{lo}–{hi}"] = float(
            (skew(sd) ** 2 + 1) / (kurtosis(sd) + 3 * (n - 1) ** 2 / ((n - 2) * (n - 3)))
        )

    trend_cv = trend.predictions["forecast"].to_numpy()
    preds = {"Window average (no multiplier)": W, "Trend model (CV)": trend_cv,
             "Role model (CV)": role_cv, "Trend + role (CV)": combined_cv}
    scores = []
    for name, p in preds.items():
        row = {"Forecast": name}
        for label, mask in (("All", everyone), ("Early season", early), ("Mid-season", ~early)):
            e, base = mse(p, mask), mse(W, mask)
            row[f"{label} MSE"] = round(e, 1)
            row[f"{label} vs. window"] = f"{100 * (1 - e / base):+.0f}%"
        scores.append(row)

    mult = {n: np.clip(np.where(W > 0, preds[n] / np.where(W > 0, W, 1), 1), *CLIP)
            for n in ("Trend model (CV)", "Trend + role (CV)")}
    stat_rows = []
    for s in COUNTING:
        i = STATS.index(s)
        actual, base = bt.next_line[:, i], f.window[:, i]
        e0 = np.mean((base - actual) ** 2)
        stat_rows.append({"Stat": s.upper(), **{
            n.replace(" (CV)", ""): f"{100 * (1 - np.mean((base * m - actual) ** 2) / e0):+.0f}%"
            for n, m in mult.items()
        }})
    out = trend.predictions.with_columns(
        pl.Series("role forecast", combined_cv),
        pl.Series("role multiplier", mult["Trend + role (CV)"]),
    )
    return RoleResult(model, sel, profiles, pl.DataFrame(spread), bimod, pl.DataFrame(scores),
                      pl.DataFrame(stat_rows), pl.DataFrame(shifts), components, bias, out)
