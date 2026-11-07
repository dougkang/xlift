"""dAB (Decay-weighted Availability Blend): the share of upcoming games a player plays (007 R3).

DB-free port of the availability report's model, with its backtested constants fixed (FR-015,
FR-017). Every game, played or missed, is weighted δ^age, where age is how many seasons before
the cutoff's season it was played. A blend of the recent window, a three-season rate and a
recency-weighted rate over the last team games, each relative to the league rate ā:

    dAB = clip(ā + B1·(w̃ − ā) + B2·(l̃ − ā) + B3·(r − ā), 0, 1).

r (the recent term) weighs the team game j games back 0.5^(j / HALF_LIFE), over the last
RECENT_GAMES team games; it's what catches a player who is out right now. It was added after the
weekly projection backtest found that missing last week is the strongest signal for the next
(analysis/weekly_availability.py; docs/weekly-availability-backtest.md).

Dates are ISO strings (`YYYY-MM-DD`), which order like dates.
"""

import numpy as np

# δ, κ and κ_w: the availability report, 2022-23 through 2025-26. ā and the blend weights:
# refit with the recent term to the next 15 team games, every Monday of 2023-24 through 2025-26
# (the weekly availability backtest).
ABAR = 0.716  # pool availability rate
DELTA = 0.05  # weight per season of age
KAPPA = 5  # long-run prior strength, in team games
KAPPA_W = 0  # window prior strength
B1, B2, B3 = 0.0377, 0.2356, 0.4271  # blend weights: window, long run, recent
HALF_LIFE = 1  # the recent term's half-life, in team games
RECENT_GAMES = 20  # team games the recent term looks back
WINDOW = 15  # window games played
LOOKBACK_SEASONS = 3  # the long-run term's reach
AGES = 6  # season ages 0..5; older games pool into age 5

# Platform injury tags (FR-016). Judgment, not fitted: one tag snapshot, no history.
TAG_MULTIPLIERS = {
    "IL": 0.3,
    "IL+": 0.3,
    "O": 0.6,
    "Q": 0.9,
    "GTD": 0.9,
    "DTD": 0.9,
    "SUSP": 0.7,
    "NA": 0.0,
}

_EMPTY = np.array([], dtype="<U10")


def season_index(season_starts: np.ndarray, dates) -> np.ndarray:
    """Index into the season list of each date (-1 before the first season)."""
    return np.searchsorted(season_starts, dates, side="right") - 1


def age_counts(
    played: np.ndarray,
    team_games: np.ndarray,
    missed: list[tuple[np.ndarray, str]],
    season_starts: np.ndarray,
    cut: str,
) -> np.ndarray | None:
    """Counts before `cut` by season age, shape (4, AGES): rows are window played, window team
    games, long-run played, long-run team games. None without played or team games.

    `missed`: inferred missed seasons as (dates, known_from); a season counts once the player
    has returned (known_from < cut)."""
    p = np.asarray(played if played is not None else _EMPTY)
    p = p[p < cut]
    t = np.asarray(team_games if team_games is not None else _EMPTY)
    known = [d for d, back in missed if back < cut]
    if known:
        t = np.sort(np.concatenate([t, *known]))
    t = t[t < cut]
    if not len(p) or not len(t):
        return None
    now = season_index(season_starts, np.array([cut]))[0]

    def ages(d):
        return np.minimum(now - season_index(season_starts, d), AGES - 1)

    def count(d):
        return np.bincount(ages(d), minlength=AGES).astype(float)

    win = p[-WINDOW:]
    # Short windows count from the player's first team game.
    span = t if len(win) < WINDOW else t[t >= win[0]]
    return np.stack(
        [
            count(win),
            count(span),
            count(p[ages(p) < LOOKBACK_SEASONS]),
            count(t[ages(t) < LOOKBACK_SEASONS]),
        ]
    )


def _shrunk(played: float, games: float, k: float) -> float:
    """Rate shrunk toward ā with prior weight k; ā itself with no weighted evidence."""
    den = games + k
    return (played + k * ABAR) / den if den > 0 else ABAR


def recent_rate(played: np.ndarray, team_games: np.ndarray, cut: str) -> float | None:
    """Recency-weighted share of the last RECENT_GAMES team games before `cut` that the player
    played, the latest weighted 1, the one before 0.5^(1 / HALF_LIFE) and so on. None without
    team games. Inferred missed seasons don't count: they're long before any recent game."""
    t = np.asarray(team_games if team_games is not None else _EMPTY)
    t = t[t < cut][-RECENT_GAMES:][::-1]
    if not len(t):
        return None
    p = np.asarray(played if played is not None else _EMPTY)
    w = 0.5 ** (np.arange(len(t)) / HALF_LIFE)
    return float((np.isin(t, p) * w).sum() / w.sum())


def dab(counts: np.ndarray | None, recent: float | None = None) -> float:
    """The blend from per-age counts and the recent rate; ā without evidence. A missing term
    adds nothing (it's taken as ā)."""
    if counts is None:
        return ABAR
    wp, wt, lp, lt = counts @ (DELTA ** np.arange(AGES))
    win = _shrunk(wp, wt, KAPPA_W)
    long = _shrunk(lp, lt, KAPPA)
    r = ABAR if recent is None else recent
    blend = ABAR + B1 * (win - ABAR) + B2 * (long - ABAR) + B3 * (r - ABAR)
    return float(np.clip(blend, 0, 1))


def tag_multiplier(status: str | None) -> float:
    """dAB × tag's multiplier for a platform status; 1.0 for healthy or unknown tags."""
    return TAG_MULTIPLIERS.get(status or "", 1.0)


def cut_after(as_of) -> str:
    """The cutoff for an as-of date: everything through that day counts."""
    return str(np.datetime64(as_of) + np.timedelta64(1, "D"))
