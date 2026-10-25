"""dAB (Decay-weighted Availability Blend): the share of upcoming games a player plays (007 R3).

DB-free port of the availability report's model, with its backtested constants fixed (FR-015,
FR-017). Every game, played or missed, is weighted δ^age, where age is how many seasons before
the cutoff's season it was played. A blend of the recent window and a three-season rate, each
shrunk toward the league rate ā:

    dAB = clip(ā + B1·(w̃ − ā) + B2·(l̃ − ā), 0, 1).

Dates are ISO strings (`YYYY-MM-DD`), which order like dates.
"""

import numpy as np

# Backtested on 2022-23 through 2025-26 (the availability report).
ABAR = 0.770113  # pool availability rate
DELTA = 0.05  # weight per season of age
KAPPA = 5  # long-run prior strength, in team games
KAPPA_W = 0  # window prior strength
B1, B2 = 0.586418, 0.144796  # blend weights: window, long run
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


def dab(counts: np.ndarray | None) -> float:
    """The blend from per-age counts; ā without evidence."""
    if counts is None:
        return ABAR
    wp, wt, lp, lt = counts @ (DELTA ** np.arange(AGES))
    win = _shrunk(wp, wt, KAPPA_W)
    long = _shrunk(lp, lt, KAPPA)
    return float(np.clip(ABAR + B1 * (win - ABAR) + B2 * (long - ABAR), 0, 1))


def tag_multiplier(status: str | None) -> float:
    """dAB × tag's multiplier for a platform status; 1.0 for healthy or unknown tags."""
    return TAG_MULTIPLIERS.get(status or "", 1.0)


def cut_after(as_of) -> str:
    """The cutoff for an as-of date: everything through that day counts."""
    return str(np.datetime64(as_of) + np.timedelta64(1, "D"))
