"""Builds player projections from the data contract (research R1, R4, R5)."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date, timedelta

from sqlalchemy import text

from ffmodel.contract.seasons import current_season
from ffmodel.core.data import (
    GameWindow,
    count_team_games_bulk,
    get_availability,
    get_last_n_games_bulk,
    get_players_with_games,
)
from ffmodel.core.model.fit import (
    RECENCY_HALF_LIFE,
    SEASON_WEIGHT,
    MeanPrior,
    PlayerProjection,
    availability_rate,
    estimate_prior,
    fit_projection,
    shrink_projection,
)
from ffmodel.core.scoring import ScoringFormat

PRIOR_LOOKBACK = timedelta(days=365)
FROM_DATA = object()  # build_projections' default prior: build it from the data
# Availability stays a short-window measure: the most recent games, as before the stat fit's
# lookback grew (research R4).
AVAILABILITY_GAMES = 15


def _fit(pid, window, fmt: ScoringFormat, as_of: date) -> PlayerProjection:
    return fit_projection(
        pid,
        window,
        fmt.base_stats,
        half_life=RECENCY_HALF_LIFE,
        season_weight=SEASON_WEIGHT,
        season=current_season(as_of),
    )


def prior_pool_windows(conn, *, window: int, as_of: date) -> dict[int, GameWindow]:
    """Game windows for the prior's pool: every player with a game in the past year."""
    ids = get_players_with_games(conn, as_of - PRIOR_LOOKBACK, as_of)
    return get_last_n_games_bulk(conn, ids, window, as_of=as_of)


def build_prior(
    conn,
    fmt: ScoringFormat,
    *,
    window: int,
    as_of: date,
    windows: Mapping[int, GameWindow] | None = None,
) -> MeanPrior | None:
    """The mean prior for these settings: the pool fit over the same window. It doesn't depend
    on which players are requested, so projections built in separate calls share it. `windows`
    are the pool's windows when the caller already has them (prior_pool_windows)."""
    if windows is None:
        windows = prior_pool_windows(conn, window=window, as_of=as_of)
    fits = [_fit(pid, w, fmt, as_of) for pid, w in windows.items()]
    idx = {s: i for i, s in enumerate(fmt.base_stats)}
    ratio_pairs = [
        (idx[c.numerator], idx[c.denominator])
        for c in fmt.categories
        if c.kind == "ratio" and c.numerator in idx and c.denominator in idx
    ]
    caps = [(idx[a], idx[b]) for a, b in fmt.subset_constraints if a in idx and b in idx]
    exempt = [idx[s] for s in fmt.unshrunk_stats if s in idx]  # the format says which (006 R4)
    return estimate_prior(fits, ratio_pairs, caps, exempt)


def build_projections(
    conn,
    player_ids: Sequence[int],
    fmt: ScoringFormat,
    *,
    window: int,
    as_of: date,
    period: tuple[date, date] | None = None,
    prior: MeanPrior | None | object = FROM_DATA,
    windows: Mapping[int, GameWindow] | None = None,
) -> dict[int, PlayerProjection]:
    """Recency-weighted fits over up to `window` games, with means shrunk toward `prior`
    (built from the data by default; None leaves them raw). Availability covers the most recent
    AVAILABILITY_GAMES of the window. `windows` may already hold some players' windows for the
    same `window` and `as_of` (e.g. the prior's pool); only the rest are fetched."""
    ids = sorted(set(player_ids))
    known = dict(windows or {})
    if prior is FROM_DATA:
        if not known:
            known = prior_pool_windows(conn, window=window, as_of=as_of)
        prior = build_prior(conn, fmt, window=window, as_of=as_of, windows=known)
    missing = [pid for pid in ids if pid not in known]
    windows = {**known, **get_last_n_games_bulk(conn, missing, window, as_of=as_of)}
    # `period` is the remaining-games window, used as given: tactical picks games by date after
    # the matchup's as-of, whatever their status in our data (005 research R2).
    remaining = (
        count_team_games_bulk(conn, ids, period[0], period[1], statuses=("scheduled", "final"))
        if period
        else dict.fromkeys(ids, 0)
    )
    out = {}
    for pid in ids:
        w = windows[pid]
        proj = shrink_projection(_fit(pid, w, fmt, as_of), prior)
        avail = None
        if w.found:
            recent = sorted(w.games, key=lambda g: (g.game_date, g.game_id))[-AVAILABILITY_GAMES:]
            start = recent[0].game_date
            if len(recent) < AVAILABILITY_GAMES:
                # The window holds every game the player has; count misses back to the start of
                # their earliest stint, not just from their first appearance (research R4).
                first_stint = conn.execute(
                    text("SELECT MIN(start_date) FROM player_team_stint WHERE player_id = :p"),
                    {"p": pid},
                ).scalar_one()
                if first_stint:
                    start = min(start, date.fromisoformat(first_stint))
            span = get_availability(conn, pid, start, as_of)
            avail = availability_rate(len(recent), span.team_games)
        out[pid] = replace(proj, availability=avail, games_remaining=remaining.get(pid, 0))
    return out
