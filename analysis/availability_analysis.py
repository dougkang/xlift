import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full", app_title="Player Availability")


@app.cell
def _():
    from datetime import date

    import altair as alt
    import marimo as mo
    import numpy as np
    import polars as pl

    import availability as av
    from ffmodel.contract.db import get_engine
    from ffmodel.core.data import get_league, get_player_details, list_leagues
    from ffmodel.core.model import build_projections
    from ffmodel.core.scenario import from_snapshot
    from ffmodel.core.scoring import get_format

    return (
        alt,
        av,
        build_projections,
        date,
        from_snapshot,
        get_engine,
        get_format,
        get_league,
        get_player_details,
        list_leagues,
        mo,
        np,
        pl,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # Player Availability

    How often does a player play? A fantasy player's value is their per-game production times
    the share of games they're available for, so a 30-point scorer who plays half the time is
    worth about as much as a 15-point scorer who never misses. This report measures
    availability, tests how well it can be predicted, and fits **dAB** (Decay-weighted
    Availability Blend), the availability model the rankings use.
    """)
    return


@app.cell
def _(date, get_engine, list_leagues, mo):
    engine = get_engine()
    with engine.connect() as _conn:
        _leagues = list_leagues(_conn)
    league_picker = mo.ui.dropdown(
        {l.name: l.league_id for l in _leagues}, value=_leagues[0].name, label="League"
    )
    as_of = mo.ui.date(value=date.today(), label="As of")
    mo.hstack([league_picker, as_of], justify="start")
    return as_of, engine, league_picker


@app.cell
def _(as_of, av, engine):
    data = av.load(engine, as_of.value)
    bt = av.backtest(data)
    result = av.fit(bt)
    with engine.connect() as _conn:
        names = dict(_conn.exec_driver_sql("SELECT player_id, full_name FROM player").all())
    return bt, data, names, result


@app.cell
def _(bt, data, mo, np, persistence, result):
    _f, _s = result.fit, result.scores
    _early = {r["Estimator"]: r["Early season vs. avg"] for r in _s.iter_rows(named=True)}
    _blend = f"dAB, δ = {_f.delta}"
    _r = persistence["r"]
    mo.callout(
        mo.md(f"""
    **Summary**

    - **The app's availability estimate fails early in a season.** One to two weeks into a
      season, its 15-game window is {_early["Window (current model)"]} against simply giving
      everyone the league average. dAB is {_early[_blend]}.
    - **Old absences fade fast.** The best offseason weight is **δ = {_f.delta}**: a game from
      last season counts about {_f.delta:.0%} as much as one from this season. Error is flat
      from 0 to 0.1, so the exact value matters little.
    - **Durability persists, weakly, at the season level.** Season-to-season availability
      correlates at r = {np.mean(_r):.2f} for rotation players (r = {min(_r):.2f}–{max(_r):.2f}
      by season pair). Over the backtest's 15-game horizon, whether a player is playing *now*
      dominates, which is why δ fits so low. A season-long ranking may want a higher δ.
    - **{len(data.gap_dates)} players have a missed season** in the loaded history. Returners
      are rare in the backtest ({persistence["returner_obs"]} observations), so their estimate
      rests on the general fit.
    - Backtest: {bt.obs.height:,} player-cutoffs over seasons
      {", ".join(sorted(bt.obs["season"].unique().to_list()))}.
    """),
        kind="info",
    )
    return


@app.cell
def _(as_of, av, bt, data, mo, np, pl):
    # Input data: what was loaded, per season.
    _seasons = []
    for _k, (_sid, _start, _end, _n) in enumerate(data.seasons):
        _played = sum(int((data.season_of(p) == _k).sum()) for p in data.played_dates.values())
        _team = sum(int((data.season_of(t) == _k).sum()) for t in data.team_dates.values())
        _missed = sum(int(data.season_of(d[:1])[0]) == _k
                      for g in data.gap_dates.values() for d, _ in g)
        _seasons.append({
            "Season": _sid, "First game": _start, "Last game": _end, "Games": _n,
            "Player-games played": _played, "Player team-games (on a roster)": _team,
            "Missed seasons added": _missed,
            "Used for": "history only" if _k == 0 else
                        ("evaluation cutoffs" if _n >= 1000 else "outlook only"),
        })
    # Sampling: every cutoff date, its position, spacing in team games, and players qualifying.
    _pos = {"early": [f"{q:.0%}" for q in av.EARLY_QS], "mid": [f"{q:.0%}" for q in av.MID_QS]}
    _cuts = bt.obs.group_by("season", "kind", "cut").len().sort("season", "cut")

    def _team_games_between(a, b):
        _n = [int(((t >= a) & (t < b)).sum()) for t in data.team_dates.values()]
        _n = [x for x in _n if x]
        return int(np.median(_n)) if _n else 0

    _rows, _gaps = [], {"early": [], "mid": []}
    for (_sid,), _g in _cuts.group_by("season", maintain_order=True):
        _prev = None
        for _r in _g.iter_rows(named=True):
            _i = _g.filter(pl.col("kind") == _r["kind"])["cut"].to_list().index(_r["cut"])
            _between = _team_games_between(_prev["cut"], _r["cut"]) if _prev else None
            if _prev and _prev["kind"] == _r["kind"]:
                _gaps[_r["kind"]].append(_between)
            _rows.append({
                "Season": _sid, "Cutoff": _r["cut"], "Kind": _r["kind"],
                "Through the season": _pos[_r["kind"]][_i],
                "Team games since previous": _between, "Player-cutoffs": _r["len"],
            })
            _prev = _r

    def _span(xs):
        return f"{min(xs)}–{max(xs)}" if min(xs) != max(xs) else f"{xs[0]}"

    def _overlap(xs, horizon):
        """How consecutive cutoffs' outcomes relate, given the games between them."""
        if max(xs) < horizon:
            return f"{_span(xs)} team games apart, so their outcomes share {horizon - max(xs)}+ games"
        if min(xs) >= horizon:
            return f"{_span(xs)} team games apart, so their outcomes don't overlap"
        return f"{_span(xs)} team games apart, so their outcomes overlap at most slightly"

    _per_player = bt.obs.group_by("pid").len()["len"]
    mo.vstack([
        mo.md(f"""
    ## Data and evaluation design

    **Input data.** NBA box scores (the stats source the app loads), **regular season only**:
    play-in, playoff, preseason and All-Star games are excluded. Two tables are combined:

    - *Games played*: one row per player per game they appeared in, with minutes.
    - *Games available*: every game the player's team played while the player was on its
      roster (team stints). Stints are built from games played, so a season with no games has
      no stint; such a season, between two seasons with games, is added as a team's worth of
      missed games (*missed seasons added*).

    A game the player's team played without them counts as missed, whatever the reason:
    injury, rest, suspension or a coach's decision. Data runs through the as-of date,
    {as_of.value}.
    """),
        mo.ui.table(pl.DataFrame(_seasons), selection=None, show_column_summaries=False),
        mo.md(f"""
    **Unit of observation.** A *player-cutoff*: one player at one cutoff date. Every input is
    strictly before the cutoff; the outcome is strictly after.

    **Sampling strategy.**

    - **Cutoff dates.** Every completed season that has a season before it contributes five
      cutoffs, placed by its game days: **early** at {", ".join(_pos["early"])} of the way
      through (the first one to two weeks, when the lookback crosses an offseason) and **mid**
      at {", ".join(_pos["mid"])}. The first loaded season serves only as history, and the
      season in progress isn't evaluated.
    - **Eligibility.** At least {av.MIN_GAMES} games played before the cutoff (any season),
      averaging at least {av.MIN_MINUTES} minutes over them, and at least 10 team games after
      it. The minutes floor keeps the sample to fantasy-relevant players; it also means
      deep-bench players, whose absences are mostly coach's decisions, aren't evaluated.
    - **Inputs.** The window is the last {av.WINDOW} games played (with the team games since
      the first of them); the long-run rate covers {av.LOOKBACK_SEASONS} seasons. Both can span
      seasons, with each game weighted δ^age.
    - **Outcome.** The share of the player's next {av.HORIZON} team games they played. A
      missed season in that span counts as missed games.
    - **Size.** {bt.obs.height:,} player-cutoffs from {bt.obs["pid"].n_unique():,} players; a
      player appears a median of {int(np.median(_per_player))} times (at most
      {int(_per_player.max())}).

    **Dependence between observations.** The same player recurs across cutoffs. Each outcome
    covers the next {av.HORIZON} team games: the two early cutoffs are
    {_overlap(_gaps["early"], av.HORIZON)}; consecutive mid-season cutoffs are
    {_overlap(_gaps["mid"], av.HORIZON)}. A long injury still shows up at several cutoffs, so
    observations aren't independent. Errors are averaged over observations.

    **Validation.**

    - **Leave one season out.** For each evaluated season, the blend weights $b_1, b_2$ are fit
      on the other seasons and scored on the held-out one. Scores for the dAB rows are computed
      this way.
    - **Chosen on all seasons (in-sample):** δ, κ and $\\kappa_w$, by grid search. The
      error-by-δ curve in section 5 is in-sample, and these choices make the CV scores
      slightly optimistic.
    - **Not chronological.** Held-out seasons are sometimes predicted from later ones, so this
      isn't a true forward test. A forward test would fit only on seasons before the one scored.
    - **Metric.** Mean squared error of the predicted share of games played, reported as the
      reduction against giving every player the pool rate $\\bar a$.
    """),
        mo.ui.table(pl.DataFrame(_rows), selection=None, page_size=20,
                    show_column_summaries=False),
    ])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. The data

    Regular-season games only. "Games available" are the games a player's team played while
    they were on the roster (their *stints*). Stints come from games played, so a season with no
    games has no stint. A season with no games between two seasons with games is treated as a
    **missed season** and added as a team's worth of missed games.
    """)
    return


@app.cell
def _(data, mo, pl):
    _rows = []
    for _k, (_sid, _start, _end, _n) in enumerate(data.seasons):
        _players = _rotation = _missed = 0
        for _pid, _p in data.played_dates.items():
            _in = data.season_of(_p) == _k
            if _in.any():
                _players += 1
                if _in.sum() >= 10 and data.played_minutes[_pid][_in].mean() >= 20:
                    _rotation += 1
        for _gaps in data.gap_dates.values():
            _missed += sum(int(data.season_of(_d[:1])[0]) == _k for _d, _ in _gaps)
        _rows.append(
            {
                "Season": _sid,
                "Games": _n,
                "Dates": f"{_start} – {_end}",
                "Players": _players,
                "Rotation players (10+ games, 20+ min)": _rotation,
                "Missed seasons": _missed,
            }
        )
    mo.ui.table(pl.DataFrame(_rows), selection=None, show_column_summaries=False)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. How much rotation players play

    Each completed season, the share of available games that rotation players (10+ games, 20+
    minutes a game) actually played. Most play nearly every game; a long tail misses large
    stretches. That tail is where availability changes a player's value.
    """)
    return


@app.cell
def _(alt, data, mo, pl):
    _rows = []
    for _k, (_sid, _, _, _n) in enumerate(data.seasons):
        if _n < 1000:
            continue
        for _pid, _p in data.played_dates.items():
            _in = data.season_of(_p) == _k
            if _in.sum() < 10 or data.played_minutes[_pid][_in].mean() < 20:
                continue
            _played, _games, _ = data.season_line(_pid, _k)
            _rows.append({"season": _sid, "availability": min(1.0, _played / _games)})
    _df = pl.DataFrame(_rows)
    _summary = _df.group_by("season").agg(
        pl.len().alias("Players"),
        pl.col("availability").median().round(2).alias("Median"),
        (pl.col("availability") < 0.5).mean().mul(100).round(0).alias("% under half"),
        (pl.col("availability") >= 0.9).mean().mul(100).round(0).alias("% at 90%+"),
    ).sort("season")
    _chart = (
        alt.Chart(_df)
        .mark_bar()
        .encode(
            x=alt.X("availability:Q", bin=alt.Bin(step=0.05), title="Share of team games played"),
            y=alt.Y("count():Q", title="Players"),
            color=alt.Color("season:N", title=None),
            tooltip=["season", "count()"],
        )
        .properties(width=360, height=220)
        .facet(column=alt.Column("season:N", title=None))
    )
    mo.vstack([_chart, mo.ui.table(_summary, selection=None, show_column_summaries=False)])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Does durability carry over?

    Each rotation player's availability in one season against the next. A missed season counts
    as 0. Players who left the league are excluded. If availability were pure luck, the
    points would show no trend. If it were fixed, they'd sit on the diagonal.
    """)
    return


@app.cell
def _(data, np, pl, result):
    _rows = []
    for _k in range(len(data.seasons) - 1):
        if data.seasons[_k + 1][3] < 1000:
            continue  # the next season is still in progress
        for _pid, _p in data.played_dates.items():
            _in = data.season_of(_p) == _k
            if _in.sum() < 10 or data.played_minutes[_pid][_in].mean() < 20:
                continue
            _p0, _t0, _ = data.season_line(_pid, _k)
            _p1, _t1, _missed = data.season_line(_pid, _k + 1)
            if not _t1:
                continue  # left the league
            _rows.append(
                {
                    "pair": f"{data.seasons[_k][0]} → {data.seasons[_k + 1][0]}",
                    "pid": _pid,
                    "this season": min(1.0, _p0 / _t0),
                    "next season": min(1.0, _p1 / _t1),
                    "missed next": _missed,
                }
            )
    yoy = pl.DataFrame(_rows)
    _r = [
        float(np.corrcoef(g["this season"], g["next season"])[0, 1])
        for _, g in yoy.group_by("pair", maintain_order=True)
    ]

    def _known_gap(pid, cut):
        _now = data.season_of(np.array([cut]))[0]
        return any(
            back < cut and _now - data.season_of(d[:1])[0] < 3 for d, back in data.gap_dates.get(pid, ())
        )

    _returners = result.predictions.filter(
        pl.struct("pid", "cut").map_elements(
            lambda r: _known_gap(r["pid"], r["cut"]), return_dtype=pl.Boolean
        )
    )
    persistence = {"r": _r, "returner_obs": _returners.height, "returners": _returners}
    return persistence, yoy


@app.cell
def _(alt, mo, pl, yoy):
    _binned = (
        yoy.with_columns((pl.col("this season") * 10).floor().clip(0, 9).alias("bin"))
        .group_by("pair", "bin")
        .agg(pl.col("this season").mean(), pl.col("next season").mean(), pl.len().alias("n"))
        .filter(pl.col("n") >= 5)
    )
    _diag = alt.Chart(pl.DataFrame({"x": [0, 1], "y": [0, 1]})).mark_line(
        color="#9aa4b2", strokeDash=[4, 4]
    ).encode(x="x:Q", y="y:Q")
    _points = alt.Chart(yoy).mark_circle(size=14, opacity=0.25).encode(
        x=alt.X("this season:Q", title="Availability, this season", scale=alt.Scale(domain=[0, 1])),
        y=alt.Y("next season:Q", title="Availability, next season", scale=alt.Scale(domain=[0, 1])),
        color=alt.Color("pair:N", title=None),
    )
    _means = alt.Chart(_binned).mark_line(point=True).encode(
        x="this season:Q", y="next season:Q", color="pair:N",
        tooltip=["pair", alt.Tooltip("this season:Q", format=".2f"),
                 alt.Tooltip("next season:Q", format=".2f"), "n"],
    )
    _table = (
        yoy.group_by("pair", maintain_order=True)
        .agg(
            pl.len().alias("Players"),
            pl.corr("this season", "next season").round(2).alias("r"),
            pl.col("missed next").sum().alias("Missed the next season"),
        )
    )
    mo.vstack(
        [
            (_diag + _points + _means).properties(width=420, height=360),
            mo.md("Lines are binned means. A flat line means this season predicts nothing about "
                  "the next."),
            mo.ui.table(_table, selection=None, show_column_summaries=False),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 4. The model: dAB (Decay-weighted Availability Blend)

    The app measures availability over the stat window. Take the player's last $W = 15$ games
    played, then count their team's games from the first of those to the as-of date:

    $$a_i^{\text{win}} = \min\!\left(1,\ \frac{W}{\text{team games since the first of the last } W
    \text{ played}}\right)$$

    Because the window *starts at a game played*, any absence before it is invisible. A player
    back from a 30-game injury who has played 15 straight looks fully available. The model
    adds a long-run rate over the last three seasons, shrinks both toward the pool rate
    $\bar a$, and blends them. That blend is **dAB**:

    $$\tilde a_i^{\text{win}} = \frac{\text{played}^{\text{win}}_i + \kappa_w\,\bar a}
    {\text{team games}^{\text{win}}_i + \kappa_w} \qquad
    a_i^{\text{long}} = \frac{\text{played}_i + \kappa\,\bar a}{\text{team games}_i + \kappa}$$

    $$a_i^{\text{dAB}} = \bar a + b_1\,(\tilde a_i^{\text{win}} - \bar a) +
    b_2\,(a_i^{\text{long}} - \bar a)$$

    **Older seasons count less.** Every game, played or missed, is weighted by its season's age
    (0 for the current season, 1 for last season, and so on):

    $$\text{played}_i = \sum_g \delta^{\,\text{age}(g)}\,[\text{played } g] \qquad
    \text{team games}_i = \sum_g \delta^{\,\text{age}(g)}$$

    **Missed seasons** count only once the player is back, because until then a missed season
    looks the same as a retirement. A season out of the league (overseas, for example) is
    indistinguishable from an injury and is counted the same way. A rookie's history starts at
    their first game.

    **Injury tags** scale the near-term outlook: $a_i = m_{\text{tag}(i)}\,
    a_i^{\text{dAB}}$. There is one tag snapshot and no history, so the multipliers $m$ are
    judgment, set with the sliders in section 6.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 5. Backtest

    The sample, outcome and validation are described in *Data and evaluation design* at the
    top. In short: five cutoffs per evaluated season, rotation players (10+ games and 20+
    minutes a game before the cutoff), and the share of their next 15 team games played.
    $\delta$, $\kappa$ and $\kappa_w$ are chosen by grid search on all seasons, and $b_1, b_2$
    by least squares, cross-validated by leaving one season out.
    """)
    return


@app.cell
def _(alt, bt, mo, pl, result):
    _f = result.fit
    _est = ["Window (current model)", "dAB"]
    _cal = (
        result.predictions.unpivot(
            index=["actual", "kind"], on=_est, variable_name="estimator", value_name="predicted"
        )
        .with_columns((pl.col("predicted") * 10).floor().clip(0, 9).alias("bin"))
        .group_by("estimator", "kind", "bin")
        .agg(pl.col("predicted").mean(), pl.col("actual").mean(), pl.len().alias("n"))
        .filter(pl.col("n") >= 15)
    )
    _diag = alt.Chart(pl.DataFrame({"x": [0, 1], "y": [0, 1]})).mark_line(
        color="#9aa4b2", strokeDash=[4, 4]
    ).encode(x="x:Q", y="y:Q")
    def _panel(kind, title):
        return alt.layer(
            _diag,
            alt.Chart(_cal.filter(pl.col("kind") == kind)).mark_line(point=True).encode(
                x=alt.X("predicted:Q", title="Predicted availability",
                        scale=alt.Scale(domain=[0, 1])),
                y=alt.Y("actual:Q", title="Share of next 15 games played",
                        scale=alt.Scale(domain=[0, 1])),
                color=alt.Color("estimator:N", sort=_est, title=None),
                tooltip=["estimator", alt.Tooltip("predicted:Q", format=".2f"),
                         alt.Tooltip("actual:Q", format=".2f"), "n"],
            ),
        ).properties(width=260, height=240, title=title)

    _calibration = alt.hconcat(_panel("early", "Early season"), _panel("mid", "Mid-season"))
    _profile = alt.layer(
        alt.Chart(result.profile).mark_line(point=True).encode(
            x=alt.X("δ:Q", title="Offseason weight δ"),
            y=alt.Y("MSE:Q", scale=alt.Scale(zero=False)),
            color=alt.Color("cutoffs:N", title=None),
            tooltip=["δ", "cutoffs", alt.Tooltip("MSE:Q", format=".4f")],
        ),
        alt.Chart(pl.DataFrame({"δ": [_f.delta]})).mark_rule(
            color="#9aa4b2", strokeDash=[4, 4]
        ).encode(x="δ:Q"),
    ).properties(width=360, height=240, title="Error by δ (in-sample)")
    _counts = bt.obs.group_by("season", "kind").len().sort("season", "kind").pivot(
        on="kind", index="season", values="len"
    )
    mo.vstack(
        [
            mo.md(
                f"**Fitted:** $\\bar a$ = {_f.abar:.3f}, **δ = {_f.delta}**, κ = {_f.kappa}, "
                f"$\\kappa_w$ = {_f.kappa_w}, $b_1$ = {_f.b1:.2f}, $b_2$ = {_f.b2:.2f}. *vs. avg* "
                "is the error reduction over giving everyone $\\bar a$."
            ),
            mo.ui.table(result.scores, selection=None, show_column_summaries=False),
            mo.md("**Calibration.** Points below the diagonal mean the estimator promised more "
                  "games than were played. Early in a season the window estimate is badly "
                  "overconfident."),
            _calibration,
            mo.md("**Choosing δ.** Early-season error rises steadily with δ: last season's "
                  "absences mostly don't carry over. Mid-season, δ barely matters, because the "
                  "current season dominates."),
            _profile,
            mo.md("Observations per season:"),
            mo.ui.table(_counts, selection=None, show_column_summaries=False),
        ]
    )
    return


@app.cell
def _(mo, names, persistence, pl):
    _r = persistence["returners"]
    _table = (
        _r.with_columns(pl.col("pid").replace_strict(names, default=None).alias("Player"))
        .select("Player", "season", "kind", "actual", "Window (current model)", "dAB")
        .sort("season", "Player")
    )
    _summary = _r.group_by("kind").agg(
        pl.len().alias("Observations"),
        pl.col("actual").mean().round(2).alias("Actual"),
        pl.col("dAB").mean().round(2).alias("dAB predicted"),
        pl.col("Window (current model)").mean().round(2).alias("Window predicted"),
    ).sort("kind")

    def _verdict(row):
        _gap = row["dAB predicted"] - row["Actual"]
        _how = ("about right" if abs(_gap) < 0.05
                else "too few games" if _gap < 0 else "too many games")
        return (f"{row['kind']}-season, it predicted {_how} ({row['dAB predicted']:.2f} vs. "
                f"{row['Actual']:.2f} actual, {row['Observations']} observations)")

    _verdicts = "; ".join(_verdict(r) for r in _summary.iter_rows(named=True)) or "no observations"
    mo.vstack(
        [
            mo.md(
                f"""
    ### Returners from a missed season

    Only **{_r.height} backtest observations** ({_r["pid"].n_unique()} players) come after a
    known missed season, too few to fit a separate weight for missed seasons. The model treats
    them like any other absence. On these few: {_verdicts}. Some gaps aren't injuries (a season
    out of the league looks the same).
    """
            ),
            mo.ui.table(_summary, selection=None, show_column_summaries=False),
            mo.ui.table(_table, selection=None, page_size=10, show_column_summaries=False),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 6. The outlook now

    The fitted model applied at the as-of date. δ defaults to the backtested value; the tag
    multipliers are judgment.
    """)
    return


@app.cell
def _(av, mo, result):
    offseason_weight = mo.ui.slider(
        0, 1, value=result.fit.delta, step=0.05, show_value=True, label="Offseason weight δ"
    )
    tag_multipliers = mo.ui.dictionary(
        {
            _group: mo.ui.slider(0, 1, value=_m, step=0.05, show_value=True)
            for _group, _m in av.DEFAULT_TAG_MULTIPLIERS.items()
        }
    )
    mo.vstack([offseason_weight, mo.md("Injury tag multipliers:"), tag_multipliers])
    return offseason_weight, tag_multipliers


@app.cell
def _(
    as_of,
    av,
    build_projections,
    data,
    engine,
    from_snapshot,
    get_format,
    get_league,
    get_player_details,
    league_picker,
):
    # League context: rosters, current tags, and the app's own window availability.
    with engine.connect() as _conn:
        snapshot = get_league(_conn, league_picker.value)
        _details = get_player_details(_conn, league_id=league_picker.value)
        status = {pid: st for pid, (_summary, st) in _details.items()}
        _recent = [
            pid for pid, p in data.played_dates.items() if len(p) and p[-1] >= data.seasons[-2][1]
        ]
        model_window = {
            pid: proj.availability
            for pid, proj in build_projections(
                _conn,
                _recent,
                get_format(snapshot.settings.scoring_format_id),
                window=av.WINDOW,
                as_of=as_of.value,
                prior=None,
            ).items()
        }
    owner = from_snapshot(snapshot).owner
    team_names = {t.fantasy_team_id: t.name for t in snapshot.teams}
    return model_window, owner, status, team_names


@app.cell
def _(
    as_of,
    av,
    data,
    mo,
    model_window,
    names,
    offseason_weight,
    owner,
    pl,
    result,
    status,
    tag_multipliers,
    team_names,
):
    _cut = av.cut_after(as_of.value)
    _rows = []
    for _pid, _team in owner.items():
        _window = model_window.get(_pid)
        if _window is None:
            continue  # no games yet: no projection, no availability
        _blend, _win_s, (_wp, _wt, _lp, _lt) = result.fit.blend(
            data.counts(_pid, _cut), offseason_weight.value
        )
        _status = status.get(_pid, "healthy")
        _adjusted = _blend * av.tag_multiplier(_status, tag_multipliers.value)
        _rows.append(
            {
                "Player": names.get(_pid, str(_pid)),
                "Team": team_names[_team],
                "Tag": _status,
                "Window (app)": round(_window, 2),
                "Window, shrunk": round(_win_s, 2),
                "Long run (weighted)": f"{_lp:.1f}/{_lt:.1f}",
                "dAB": round(_blend, 2),
                "dAB × tag": round(_adjusted, 2),
                "Change": round(_adjusted - _window, 2),
            }
        )
    mo.vstack(
        [
            mo.md("**Rostered players, biggest changes first.** *dAB × tag* includes the tag "
                  "multiplier; the app's window doesn't."),
            mo.ui.table(
                pl.DataFrame(_rows).sort(pl.col("Change").abs(), descending=True),
                selection=None,
                page_size=15,
                show_column_summaries=False,
            ),
        ]
    )
    return


@app.cell
def _(mo, model_window, names):
    # Players with well-known injury histories, then durable ones and rookies for contrast.
    _defaults = [
        "Joel Embiid", "Anthony Davis", "Ja Morant", "Paul George", "Zach LaVine", "Trae Young",
        "Walker Kessler", "Domantas Sabonis", "Bradley Beal", "Kawhi Leonard", "Zion Williamson",
        "Tyrese Haliburton", "Damian Lillard", "Kyrie Irving", "Nikola Jokić", "Mikal Bridges",
        "Scottie Barnes", "Jalen Brunson", "Cameron Boozer",
    ]
    _options = sorted({names[p] for p in model_window if p in names})
    compare_players = mo.ui.multiselect(
        options=_options, value=[n for n in _defaults if n in _options], label="Players"
    )
    return (compare_players,)


@app.cell
def _(
    as_of,
    av,
    compare_players,
    data,
    mo,
    model_window,
    names,
    pl,
    result,
    status,
):
    _cut = av.cut_after(as_of.value)
    _deltas = sorted({0.0, 0.1, 0.2, 0.5, 1.0, result.fit.delta})
    _ids = {n: p for p, n in names.items() if p in model_window}
    _shown = range(max(0, len(data.seasons) - 4), len(data.seasons))

    def _cell(pid, k):
        _p, _t, _missed = data.season_line(pid, k)
        return "missed" if _missed else f"{_p}/{_t}" if _t else "–"

    def _bucket(pid):
        _p, _t, _missed = data.season_line(pid, len(data.seasons) - 2)
        if _missed:
            return "Missed last season"
        if not _t:
            return "No games last season (rookie or new)"
        _share = _p / _t
        return ("< 25%" if _share < 0.25 else "25–50%" if _share < 0.5
                else "50–75%" if _share < 0.75 else "≥ 75%")

    _rows = []
    for _name in compare_players.value:
        _pid = _ids[_name]
        _c = data.counts(_pid, _cut)
        _row = {"Player": _name, "Tag": status.get(_pid, "healthy")}
        _row |= {data.seasons[k][0]: _cell(_pid, k) for k in _shown}
        _row["Window (app)"] = round(model_window[_pid], 2)
        _row |= {f"δ = {d}": round(result.fit.blend(_c, d)[0], 2) for d in _deltas}
        _rows.append(_row)

    _all = [
        {"Last season": _bucket(_pid),
         **{f"δ = {d}": result.fit.blend(data.counts(_pid, _cut), d)[0] for d in _deltas}}
        for _pid in model_window
    ]
    _order = ["Missed last season", "< 25%", "25–50%", "50–75%", "≥ 75%",
              "No games last season (rookie or new)"]
    _summary = (
        pl.DataFrame(_all)
        .group_by("Last season")
        .agg(pl.len().alias("Players"), *[pl.col(f"δ = {d}").mean().round(2) for d in _deltas])
        .sort(pl.col("Last season").replace_strict(_order, list(range(len(_order)))))
    )
    mo.vstack(
        [
            mo.md(
                "**Players across seasons**, dAB before tags at several δ "
                f"(the backtest picks δ = {result.fit.delta})."
            ),
            compare_players,
            mo.ui.table(pl.DataFrame(_rows), selection=None, page_size=20,
                        show_column_summaries=False),
            mo.md("By share of last season's team games played (everyone who played since last "
                  "season began):"),
            mo.ui.table(_summary, selection=None, show_column_summaries=False),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 7. Caveats and next steps

    - **Missed seasons are inferred**, not recorded. A season out of the league reads as a
      missed season, and returners are too rare in the backtest to calibrate on their own.
    - **Rookies aren't in the backtest**, which requires 10+ games before a cutoff, so their
      early-season estimate is an extrapolation.
    - **Tag multipliers are judgment.** A history of tag snapshots would let them be fit.
    - **The horizon is the next 15 games.** A season-long ranking may want a longer horizon,
      where durability history matters more and δ would likely fit higher.
    - **The app still uses the window estimate.** Moving this model into the backend would
      fix Impact Analysis's early-season availability.
    """)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
