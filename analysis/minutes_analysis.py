import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Minutes Trend")


@app.cell
def _():
    from datetime import date

    import altair as alt
    import marimo as mo
    import numpy as np
    import polars as pl

    import minutes as mn
    from ffmodel.contract.db import get_engine
    from ffmodel.core.data import get_league, list_leagues
    from ffmodel.core.scenario import from_snapshot

    return (
        alt,
        date,
        from_snapshot,
        get_engine,
        get_league,
        list_leagues,
        mn,
        mo,
        np,
        pl,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # Minutes Trend

    A projection averages a player's last 15 games, so it describes the role they *had*. When a
    role changes, say a starter is benched by new signings or a reserve is promoted, the
    projection lags behind. This report tests two ways to see a change coming:

    - **Trend:** do recent minutes predict where minutes are heading?
    - **Roles:** do minutes cluster into roles (starters, rotation players, bench), and does a
      player drifting toward another role predict their minutes?

    Together they give a **minutes trend multiplier** for counting stats that penalizes falling
    minutes and boosts rising ones. It stands alone for now; the rankings don't use it yet.
    """)
    return


@app.cell
def _(date, get_engine, list_leagues, mn, mo):
    engine = get_engine()
    with engine.connect() as _conn:
        _leagues = list_leagues(_conn)
    league_picker = mo.ui.dropdown(
        {l.name: l.league_id for l in _leagues}, value=_leagues[0].name, label="League"
    )
    as_of = mo.ui.date(value=date.today(), label="As of")
    role_k = mo.ui.dropdown(
        [str(k) for k in mn.ROLE_K_GRID], value="5", label="Roles"
    )
    mo.hstack([league_picker, as_of, role_k], justify="start")
    return as_of, engine, league_picker, role_k


@app.cell
def _(as_of, engine, mn, role_k):
    logs = mn.load(engine, as_of.value)
    bt = mn.backtest(logs)
    result = mn.fit(bt)
    roles = mn.fit_roles(bt, result, k=int(role_k.value))
    with engine.connect() as _conn:
        names = dict(_conn.exec_driver_sql("SELECT player_id, full_name FROM player").all())
    return bt, logs, names, result, roles


@app.cell
def _(bt, mo, result, roles, symmetry):
    _m = result.model
    _row = {r["Forecast"]: r for r in roles.scores.iter_rows(named=True)}
    _w = "vs. window"
    _trend, _both = _row["Trend model (CV)"], _row["Trend + role (CV)"]
    _stats = {r["Stat"]: r["Trend + role"] for r in roles.stat_scores.iter_rows(named=True)}
    _shift = roles.shifts
    _new = ", ".join(_shift["Next 15 match new role"].to_list())
    _old = ", ".join(_shift["Next 15 match old role"].to_list())
    _bimod = max(roles.bimodality.values())
    _comp = {r["Forecast"]: r["vs. window"] for r in roles.components.iter_rows(named=True)}
    _roles = "; ".join(
        f"**{r['Role'].lower()}** ({r['Mean minutes']:.0f} min, spread {r['Game-to-game spread']:.0f}, "
        f"{r['Points']:.0f} pts)"
        for r in roles.profiles.iter_rows(named=True)
    )
    mo.callout(
        mo.md(f"""
    **Summary**

    - **Recent minutes predict future minutes better than the window does.** The trend model
      cuts minutes error by {_trend[f"All {_w}"]} ({_trend[f"Early season {_w}"]} early in a
      season, when roles reshuffle). Adding roles takes it to **{_both[f"All {_w}"]}**
      ({_both[f"Early season {_w}"]} early, {_both[f"Mid-season {_w}"]} mid-season).
    - **The multiplier improves stat projections:** points {_stats["PTS"]}, rebounds
      {_stats["REB"]}, assists {_stats["AST"]}, and smaller gains for the other counting stats.
    - **Players fall into recognizable roles, along a continuum.** With minutes, spread and
      usage, five roles separate: {_roles}. There are no clean gaps between them, and at a
      given average minutes the spreads aren't bimodal (coefficient ≤ {_bimod:.2f}, below
      0.555). Two to five roles predict about equally well; this report uses
      {roles.model.roles.k}.
    - **Role shifts are real, but the trend already sees them.** When the last 5 games point to
      a different role than the window, the next 15 games land in the new role {_new} of the
      time (by season), against {_old} for the old one. Yet adding role *drift* to the trend
      model gives {_comp["Trend + role drift"]}, no better than the trend alone
      ({_comp["Trend only"]}). What helps is role *level*
      ({_comp["Trend + role level"]}): minutes revert toward the typical level of the player's
      role. Bench minutes tend to rise and starters' to dip slightly.
    - **Trends need smoothing, and falling and rising minutes get the same weight.** Raw trend
      lines and last-5-games averages are worse than no adjustment. Fit separately, a drop gets
      β = {symmetry["down"]:.2f} and a rise β = {symmetry["up"]:.2f}, with no gain from the split.
    - Backtest: {bt.obs.height:,} player-cutoffs over seasons
      {", ".join(sorted(bt.obs["season"].unique().to_list()))}. Trend half-life
      {_m.half_life} games, last season's games weighted {_m.delta:.0%}.
    """),
        kind="info",
    )
    return


@app.cell
def _(as_of, bt, logs, mn, mo, np, pl):
    # Input data: what was loaded, per season.
    _seasons = []
    for _k, (_sid, _start, _end, _n) in enumerate(logs.seasons):
        _games = sum(int((logs.season_of(d) == _k).sum()) for d in logs.dates.values())
        _players = sum(1 for d in logs.dates.values() if (logs.season_of(d) == _k).any())
        _seasons.append({
            "Season": _sid, "First game": _start, "Last game": _end, "Games": _n,
            "Player-games": _games, "Players": _players,
            "Used for": "history only" if _k == 0 else
                        ("evaluation cutoffs" if _n >= 1000 else "live multipliers only"),
        })
    # Sampling: every cutoff date, its position in the season, and how many players qualified.
    _pos = {"early": [f"{q:.0%}" for q in mn.EARLY_QS], "mid": [f"{q:.0%}" for q in mn.MID_QS]}
    _cuts = (
        bt.obs.group_by("season", "kind", "cut").len().sort("season", "cut")
        .with_columns(pl.col("cut").str.to_date().alias("_d"))
    )
    def _games_between(a, b):
        """Median games played between two dates, over players who played in between."""
        _n = [int(((d >= a) & (d < b)).sum()) for d in logs.dates.values()]
        _n = [x for x in _n if x]
        return int(np.median(_n)) if _n else 0

    _rows, _gaps = [], {"early": [], "mid": []}
    for (_sid,), _g in _cuts.group_by("season", maintain_order=True):
        _prev = None
        for _r in _g.iter_rows(named=True):
            _i = _g.filter(pl.col("kind") == _r["kind"])["cut"].to_list().index(_r["cut"])
            _between = _games_between(_prev["cut"], _r["cut"]) if _prev else None
            if _prev and _prev["kind"] == _r["kind"]:
                _gaps[_r["kind"]].append(_between)
            _rows.append({
                "Season": _sid, "Cutoff": _r["cut"], "Kind": _r["kind"],
                "Through the season": _pos[_r["kind"]][_i],
                "Days since previous": (_r["_d"] - _prev["_d"]).days if _prev else None,
                "Games since previous": _between,
                "Player-cutoffs": _r["len"],
            })
            _prev = _r

    def _span(xs):
        return f"{min(xs)}–{max(xs)}" if min(xs) != max(xs) else f"{xs[0]}"

    def _overlap(xs, horizon):
        """How consecutive cutoffs' outcomes relate, given the games between them."""
        if max(xs) < horizon:
            return f"{_span(xs)} games apart, so their outcomes share {horizon - max(xs)}+ games"
        if min(xs) >= horizon:
            return f"{_span(xs)} games apart, so their outcomes don't overlap"
        return f"{_span(xs)} games apart, so their outcomes overlap at most slightly"
    _per_player = bt.obs.group_by("pid").len()["len"]
    _horizon = (~np.isnan(bt.next_minutes)).sum(1)
    mo.vstack([
        mo.md(f"""
    ## Data and evaluation design

    **Input data.** NBA box scores (the stats source the app loads), **regular season only**:
    play-in, playoff, preseason and All-Star games are excluded. One row per player per game
    *played*; games a player didn't appear in have no row, so every minutes figure here is
    minutes **when playing** (games missed are availability's job). Fields used: minutes,
    FGA, FTA and turnovers (for usage), and points, rebounds, assists, steals, blocks, threes
    and turnovers (for the stat check). Data runs through the as-of date, {as_of.value}.
    """),
        mo.ui.table(pl.DataFrame(_seasons), selection=None, show_column_summaries=False),
        mo.md(f"""
    **Unit of observation.** A *player-cutoff*: one player at one cutoff date. Everything the
    model sees is strictly before the cutoff; the outcome is strictly after.

    **Sampling strategy.**

    - **Cutoff dates.** Every completed season that has a season before it contributes five
      cutoffs, placed by its game days: **early** at {", ".join(_pos["early"])} of the way
      through (the first one to two weeks, when the lookback crosses an offseason) and **mid**
      at {", ".join(_pos["mid"])}. The first loaded season serves only as history, and the
      season in progress isn't evaluated.
    - **Eligibility.** Every player with at least {mn.MIN_GAMES} games played before the
      cutoff (any season) and at least {mn.MIN_NEXT} games played in the next {mn.HORIZON}
      after it. There's no minutes floor, so bench players are included.
    - **Features.** The window is the last {mn.WINDOW} games played before the cutoff; the
      recency-weighted mean reaches back {mn.RECENT}. Both can span seasons.
    - **Outcome.** Average minutes, and each counting stat, over the player's next up to
      {mn.HORIZON} games played. Median games observed: {int(np.median(_horizon))}; {np.mean(_horizon == mn.HORIZON):.0%}
      of observations have all {mn.HORIZON} (fewer near a season's end).
    - **Size.** {bt.obs.height:,} player-cutoffs from {bt.obs["pid"].n_unique():,} players; a
      player appears a median of {int(np.median(_per_player))} times (at most
      {int(_per_player.max())}).

    **Dependence between observations.** The same player recurs across cutoffs, so
    observations aren't independent. Each outcome covers the next {mn.HORIZON} games: the two
    early cutoffs are {_overlap(_gaps["early"], mn.HORIZON)}; consecutive mid-season cutoffs
    are {_overlap(_gaps["mid"], mn.HORIZON)}. *Games since previous* in the table is the median
    over players who played in between. Errors are averaged over observations,
    so a player with more cutoffs counts more.

    **Validation.**

    - **Leave one season out.** For each evaluated season, the weights (β) and the roles
      (mixture, per-role game distributions, role minutes levels) are fit on the other seasons
      and scored on the held-out one. Every score marked *(CV)* is computed this way.
    - **Chosen on all seasons (in-sample):** the trend half-life and earlier-season weight δ, by
      grid search. These two choices make the CV scores slightly optimistic. The number of roles
      is set by the *Roles* dropdown; the role table compares all counts on CV scores.
    - **Not chronological.** Held-out seasons are sometimes predicted from later ones, so this
      isn't a true forward test. A forward test would fit only on seasons before the one
      scored.
    - **Metric.** Mean squared error of next-15 average minutes, reported as the reduction
      against the window average (no multiplier). The stat check does the same for each
      counting stat with window average × multiplier.
    """),
        mo.ui.table(pl.DataFrame(_rows), selection=None, page_size=20,
                    show_column_summaries=False),
    ])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. How often roles change

    For every player at every backtest cutoff: average minutes over their next 15 games played,
    minus their window's average. Most players stay within a few minutes of their window, but
    the tails are wide: these are the role changes a window can't see.
    """)
    return


@app.cell
def _(alt, mo, pl, result):
    _p = result.predictions.with_columns(
        (pl.col("actual") - pl.col("window")).alias("change"),
    )
    _summary = _p.group_by("kind").agg(
        pl.len().alias("Observations"),
        (pl.col("change").abs() >= 5).mean().mul(100).round(0).alias("% changed 5+ min"),
        (pl.col("change") <= -5).mean().mul(100).round(0).alias("% fell 5+"),
        (pl.col("change") >= 5).mean().mul(100).round(0).alias("% rose 5+"),
        pl.col("change").abs().median().round(1).alias("Median |change|"),
    ).sort("kind")
    # Counted here: Altair caps charts at 5,000 rows.
    _hist = (
        _p.with_columns(pl.col("change").clip(-20, 20).round(0).alias("bin"))
        .group_by("kind", "bin")
        .len()
    )
    _chart = (
        alt.Chart(_hist)
        .mark_bar()
        .encode(
            x=alt.X("bin:Q", title="Next 15 games' minutes − window minutes"),
            y=alt.Y("len:Q", title="Player-cutoffs", stack=True),
            color=alt.Color("kind:N", title=None),
            tooltip=["kind", "bin", "len"],
        )
        .properties(width=520, height=220)
    )
    mo.vstack([_chart, mo.ui.table(_summary, selection=None, show_column_summaries=False)])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. Do minutes cluster into roles?

    The hypothesis: players fall into roles (bench, role player, platoon, starter, star), each
    with its own *distribution* of minutes, not just a different average. Each player's window
    is described by three numbers: their mean minutes, the game-to-game **spread** of their
    minutes, and their **usage**, possessions used per minute (FGA + 0.44 FTA + TOV, divided by
    minutes). Spread is the interquartile range ÷ 1.349, which equals the SD for normally
    distributed minutes but ignores a one-off short game such as an injury exit. Minutes alone
    can't tell a star from a regular starter, since both play 30–36 minutes; usage can.
    """)
    return


@app.cell
def _(bt, mn, np, pl, roles):
    _X = mn.role_features(bt.f.minutes[:, : mn.WINDOW], bt.f.poss[:, : mn.WINDOW])
    _lab = roles.model.roles.label(bt.f.minutes[:, : mn.WINDOW], bt.f.poss[:, : mn.WINDOW])
    _names = roles.model.roles.names
    _bimod = pl.DataFrame(
        [{"Mean minutes": b, "Bimodality coefficient": round(v, 2)}
         for b, v in roles.bimodality.items()]
    )
    role_spread = roles.spread.join(_bimod, on="Mean minutes")
    # Scatter of a sample (Altair caps charts at 5,000 rows).
    _idx = np.random.default_rng(0).choice(len(_X), min(4000, len(_X)), replace=False)
    role_points = pl.DataFrame(
        {"Mean minutes": _X[_idx, 0], "SD": _X[_idx, 1],
         "Role": [_names[c] for c in _lab[_idx]]}
    )
    _rm = roles.model.roles
    role_dist = pl.DataFrame(
        [{"Role": _names[c], "Minutes": float(mn.ROLE_BINS[i]) + 1.5,
          "Share of games": float(np.exp(_rm.loglik[c][i]))}
         for c in range(_rm.k) for i in range(len(mn.ROLE_BINS) - 1)]
    )
    return role_dist, role_points, role_spread


@app.cell
def _(alt, mo, role_dist, role_points, role_spread, roles):
    _names = list(roles.model.roles.names)
    _scatter = alt.Chart(role_points).mark_circle(size=10, opacity=0.35).encode(
        x=alt.X("Mean minutes:Q", scale=alt.Scale(domain=[0, 42])),
        y=alt.Y("SD:Q", title="Game-to-game spread of minutes"),
        color=alt.Color("Role:N", sort=_names, title=None),
    ).properties(width=320, height=260, title="Each window: mean vs. spread")
    _shapes = alt.Chart(role_dist).mark_line(interpolate="step-after").encode(
        x=alt.X("Minutes:Q", title="Minutes in a single game", scale=alt.Scale(domain=[0, 51])),
        y=alt.Y("Share of games:Q", axis=alt.Axis(format="%")),
        color=alt.Color("Role:N", sort=_names, title=None),
    ).properties(width=320, height=260, title="Single-game minutes by role")
    mo.vstack(
        [
            mo.md(
                "**Spread by average minutes.** Starters (28+) are the steadiest and the 12–20 "
                "group swings most. A bimodality coefficient above 0.555 would suggest two "
                "groups (steady and volatile) at the same average; none comes close."
            ),
            mo.ui.table(role_spread, selection=None, show_column_summaries=False),
            mo.hstack([_scatter, _shapes], widths=[1, 1]),
            mo.md(
                "**How many roles?** Fewer roles separate more cleanly (silhouette) while BIC "
                "keeps preferring more, the signature of a continuum rather than distinct "
                "groups. Prediction is what decides, and two to five roles predict about "
                "equally well. Change *Roles* at the top to compare."
            ),
            mo.ui.table(roles.selection, selection=None, show_column_summaries=False),
            mo.md("**The roles** (fitted on every backtest window):"),
            mo.ui.table(roles.profiles, selection=None, show_column_summaries=False),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Comparing clusterings

    The same windows grouped into 2 to 5 roles, seen two ways: minutes against game-to-game
    spread (top) and against usage (bottom). Ellipses are each role's mixture component (2 SD,
    sliced to that plane). Colors run from the lowest-minutes role (light) to the highest
    (dark), and legends give each role's averages.

    **Naming** comes from each role's profile, not its position. With five roles:
    **star** has the most minutes and usage combined, **bench** the fewest minutes,
    **platoon** the widest spread, and of the two left the higher-usage one is the
    **starter** and the other the **role player**. With fewer roles, names follow mean
    minutes, and a middle role whose spread is far above the others' (1.4× their median) is the
    platoon.
    """)
    return


@app.cell
def _(bt, mn, np, pl):
    _f, _y = bt.f, bt.next_line[:, 0]
    _X = mn.role_features(_f.minutes[:, : mn.WINDOW], _f.poss[:, : mn.WINDOW])
    _idx = np.random.default_rng(0).choice(len(_X), min(2000, len(_X)), replace=False)
    _t = np.linspace(0, 2 * np.pi, 60)
    clusterings = {}
    for _k in mn.ROLE_K_GRID:
        _rm = mn.fit_roles_model(_f, _y, _k)
        _lab = _rm.label(_f.minutes[:, : mn.WINDOW], _f.poss[:, : mn.WINDOW])
        _legend = [
            f"{_rm.names[c]}: {_X[_lab == c, 0].mean():.0f} min, spread {_X[_lab == c, 1].mean():.1f},"
            f" usage {_X[_lab == c, 2].mean():.2f}"
            for c in range(_k)
        ]
        _points = pl.DataFrame({
            "Mean minutes": _X[_idx, 0], "SD": _X[_idx, 1], "Usage": _X[_idx, 2],
            "Role": [_legend[c] for c in _lab[_idx]],
        })
        # Each component's 2-SD ellipse in two planes (mean vs. SD, mean vs. usage), in raw units.
        _ell = []
        for _comp in range(_k):
            _role = int(_rm.order[_comp])
            for _plane, (_a, _b) in (("SD", (0, 1)), ("Usage", (0, 2))):
                _cov = _rm.gmm.covariances_[_comp][np.ix_([_a, _b], [_a, _b])]
                _vals, _vecs = np.linalg.eigh(_cov)
                _circle = np.c_[np.cos(_t), np.sin(_t)] * (2 * np.sqrt(_vals))
                _z = _rm.gmm.means_[_comp][[_a, _b]] + _circle @ _vecs.T
                _xy = _z * _rm.scale[[_a, _b]] + _rm.center[[_a, _b]]
                _ell += [{"Role": _legend[_role], "Plane": _plane, "Mean minutes": float(x),
                          "y": float(v), "i": i} for i, (x, v) in enumerate(_xy)]
        _dist = pl.DataFrame([
            {"Role": _legend[c], "Minutes": float(mn.ROLE_BINS[i]) + 1.5,
             "Share of games": float(np.exp(_rm.loglik[c][i]))}
            for c in range(_k) for i in range(len(mn.ROLE_BINS) - 1)
        ])
        _profile = pl.DataFrame([
            {"Roles (k)": _k, "Role": _rm.names[c], "Share": f"{np.mean(_lab == c):.0%}",
             "Mean minutes": round(float(_X[_lab == c, 0].mean()), 1),
             "Game-to-game spread": round(float(_X[_lab == c, 1].mean()), 1),
             "Usage per minute": round(float(_X[_lab == c, 2].mean()), 3),
             "Next 15 games' minutes": round(float(_rm.next_minutes[c]), 1)}
            for c in range(_k)
        ])
        clusterings[_k] = {"labels": _lab, "legend": _legend, "points": _points,
                           "ellipses": pl.DataFrame(_ell), "dist": _dist, "profile": _profile}
    return (clusterings,)


@app.cell
def _(alt, clusterings, mo, pl):
    def _scatter(k, plane):
        c = clusterings[k]
        legend = alt.Legend(title=None, orient="bottom", columns=1, labelLimit=260)
        color = alt.Color("Role:N", sort=c["legend"], scale=alt.Scale(scheme="viridis", reverse=True),
                          legend=legend if plane == "Usage" else None)
        y_axis = {
            "SD": alt.Y("SD:Q", title="Game-to-game spread", scale=alt.Scale(domain=[0, 16])),
            "Usage": alt.Y("Usage:Q", title="Usage per minute", scale=alt.Scale(domain=[0.1, 1.0])),
        }[plane]
        dots = alt.Chart(c["points"]).mark_circle(size=8, opacity=0.35).encode(
            x=alt.X("Mean minutes:Q", scale=alt.Scale(domain=[0, 42])), y=y_axis, color=color,
        )
        rings = alt.Chart(
            c["ellipses"].filter(pl.col("Plane") == plane).rename({"y": plane})
        ).mark_line(strokeWidth=2).encode(
            x="Mean minutes:Q", y=f"{plane}:Q", color=color, detail="Role:N", order="i:Q",
        )
        return (dots + rings).properties(width=210, height=190,
                                         title=f"{k} roles" if plane == "SD" else "")

    def _shapes(k):
        c = clusterings[k]
        return alt.Chart(c["dist"]).mark_line(interpolate="step-after").encode(
            x=alt.X("Minutes:Q", title="Minutes in a game", scale=alt.Scale(domain=[0, 51])),
            y=alt.Y("Share of games:Q", axis=alt.Axis(format="%")),
            color=alt.Color("Role:N", sort=c["legend"],
                            scale=alt.Scale(scheme="viridis", reverse=True), legend=None),
        ).properties(width=210, height=150)

    _ks = sorted(clusterings)
    mo.vstack(
        [
            alt.vconcat(
                alt.hconcat(*[_scatter(k, "SD") for k in _ks]).resolve_scale(color="independent"),
                alt.hconcat(*[_scatter(k, "Usage") for k in _ks]).resolve_scale(
                    color="independent"
                ),
            ),
            mo.md("Single-game minutes in each role (same colors as above):"),
            alt.hconcat(*[_shapes(k) for k in _ks]).resolve_scale(color="independent"),
            mo.ui.table(pl.concat([clusterings[k]["profile"] for k in _ks]), selection=None,
                        page_size=20, show_column_summaries=False),
        ]
    )
    return


@app.cell
def _(clusterings, mo):
    _opts = [str(k) for k in sorted(clusterings)]
    compare_a = mo.ui.dropdown(_opts, value="3", label="Rows: roles")
    compare_b = mo.ui.dropdown(_opts, value=_opts[-1], label="Columns: roles")
    mo.hstack([compare_a, compare_b], justify="start")
    return compare_a, compare_b


@app.cell
def _(alt, clusterings, compare_a, compare_b, mo, pl):
    _a, _b = clusterings[int(compare_a.value)], clusterings[int(compare_b.value)]
    _cross = (
        pl.DataFrame({
            "Rows": [_a["legend"][c] for c in _a["labels"]],
            "Columns": [_b["legend"][c] for c in _b["labels"]],
        })
        .group_by("Rows", "Columns")
        .len()
        .with_columns((pl.col("len") / pl.col("len").sum().over("Rows")).alias("Share of row"))
    )
    _heat = alt.Chart(_cross).mark_rect().encode(
        x=alt.X("Columns:N", sort=_b["legend"], title=f"{compare_b.value} roles",
                axis=alt.Axis(labelAngle=-30, labelLimit=220)),
        y=alt.Y("Rows:N", sort=_a["legend"], title=f"{compare_a.value} roles",
                axis=alt.Axis(labelLimit=220)),
        color=alt.Color("Share of row:Q", scale=alt.Scale(scheme="blues"), legend=alt.Legend(format="%")),
        tooltip=["Rows", "Columns", alt.Tooltip("Share of row:Q", format=".0%"),
                 alt.Tooltip("len:Q", title="Windows")],
    )
    _text = _heat.mark_text(fontSize=11).encode(
        text=alt.Text("Share of row:Q", format=".0%"),
        color=alt.condition("datum['Share of row'] > 0.5", alt.value("white"), alt.value("black")),
    )
    mo.vstack(
        [
            mo.md("**How the clusterings nest.** Each row's windows, spread across the other "
                  "clustering's roles. Mostly one cell per row means the finer clustering just "
                  "subdivides the coarser one; a row spread across cells means the two cut "
                  "the continuum differently."),
            (_heat + _text).properties(width=420, height=60 * int(compare_a.value)),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. The model

    **Trend.** With $W_i$ the mean minutes over the window (the player's last 15 games) and
    $R_i$ a recency-weighted mean over their last 30:

    $$R_i = \frac{\sum_j w_j\, \text{min}_{ij}}{\sum_j w_j} \qquad
    w_j = 0.5^{\,j/h} \times \begin{cases} \delta & \text{game from an earlier season} \\
    1 & \text{otherwise} \end{cases}$$

    where $j$ is games ago (0 = most recent) and $h$ the half-life.

    **Roles.** A Gaussian mixture over each window's mean minutes, game-to-game spread and
    usage (possessions used per minute) defines $K$ roles.
    Each role $k$ has a distribution of single-game minutes $L_k$ and of single-game usage
    $U_k$ (games of 5+ minutes), and a typical minutes level over the next 15 games, $\mu_k$.
    The window's older 10 games give a prior over roles $\pi_{ik}$, and the last 5 update it:

    $$P(k \mid i) \propto \pi_{ik} \prod_{j<5} \big[L_k(\text{min}_{ij})\,
    U_k(\text{use}_{ij})\big]^{\omega_j} \qquad F_i = \sum_k P(k \mid i)\, \mu_k$$

    with $\omega_j = \delta$ for a game from an earlier season and 1 otherwise. Usage keeps a
    low-usage player on a heavy-minutes stretch from reading as star. $F_i$ is the
    minutes expected for the role the player now seems to be in.

    **Forecast and multiplier.**

    $$\hat{\text{min}}_i = W_i + \beta_t\,(R_i - W_i) + \beta_r\,(F_i - W_i) \qquad
    m_i = \operatorname{clip}\!\left(\frac{\hat{\text{min}}_i}{W_i},\ 0.25,\ 2\right)$$

    A counting stat's projection becomes $m_i \times$ its window average. Percentages and
    per-minute production are unchanged. The multiplier covers minutes *when playing*; games
    missed belong to availability (dAB), so the two don't double-count.

    $h$ and $\delta$ are chosen by grid search and the β's by least squares. Errors are
    cross-validated by leaving one season out, with the roles refit on the training seasons
    each time. Cutoffs are one and two weeks into each season and 45%, 65% and 85% of the way
    through. Players need 10+ games before the cutoff and 5+ after it.
    """)
    return


@app.cell
def _(bt, mn, np, result):
    # Do falling and rising minutes deserve different weights? Fit β separately for each.
    _f, _y = bt.f, bt.next_line[:, 0]
    _W = _f.window[:, 0]
    _x = mn.recent_mean(_f, result.model.half_life, result.model.delta) - _W
    _X = np.c_[np.minimum(_x, 0), np.maximum(_x, 0)]
    _b = np.linalg.lstsq(_X, _y - _W, rcond=None)[0]
    _season = bt.obs["season"].to_numpy()

    def _cv(X):
        _out = np.empty(len(_y))
        for _s in np.unique(_season):
            _te = _season == _s
            _out[_te] = _W[_te] + X[_te] @ np.linalg.lstsq(X[~_te], (_y - _W)[~_te], rcond=None)[0]
        return float(np.mean((_out - _y) ** 2))

    symmetry = {"down": float(_b[0]), "up": float(_b[1]), "mse_split": _cv(_X),
                "mse_one": _cv(_x[:, None])}
    return (symmetry,)


@app.cell
def _(mo):
    mo.md(r"""
    ## 4. Backtest
    """)
    return


@app.cell
def _(alt, mo, pl, result, roles, symmetry):
    _m, _c = result.model, roles.model
    _grid = alt.Chart(result.grid).mark_rect().encode(
        x=alt.X("half-life:O", title="Half-life (games)"),
        y=alt.Y("δ:O", title="Earlier-season weight δ", sort="descending"),
        color=alt.Color("MSE:Q", scale=alt.Scale(scheme="blues", reverse=True), title="MSE"),
        tooltip=["half-life", "δ", alt.Tooltip("β:Q", format=".2f"),
                 alt.Tooltip("MSE:Q", format=".2f")],
    ).properties(width=300, height=220, title="Trend: minutes error by half-life and δ")
    _p = roles.predictions
    _bins = (
        _p.with_columns((pl.col("role forecast") / 3).floor().mul(3).alias("bin"))
        .group_by("kind", "bin")
        .agg(pl.col("role forecast").mean(), pl.col("actual").mean(), pl.len().alias("n"))
        .filter(pl.col("n") >= 20)
    )
    _diag = alt.Chart(pl.DataFrame({"x": [0, 40], "y": [0, 40]})).mark_line(
        color="#9aa4b2", strokeDash=[4, 4]
    ).encode(x="x:Q", y="y:Q")
    _cal = (
        _diag
        + alt.Chart(_bins).mark_line(point=True).encode(
            x=alt.X("role forecast:Q", title="Forecast minutes (trend + role)"),
            y=alt.Y("actual:Q", title="Actual minutes, next 15 games"),
            color=alt.Color("kind:N", title=None),
            tooltip=["kind", alt.Tooltip("role forecast:Q", format=".1f"),
                     alt.Tooltip("actual:Q", format=".1f"), "n"],
        )
    ).properties(width=300, height=220, title="Calibration in minutes")

    def _band(m):
        return ("≤ 0.6" if m <= 0.6 else "0.6–0.8" if m <= 0.8 else "0.8–0.95" if m <= 0.95
                else "0.95–1.05" if m <= 1.05 else "1.05–1.2" if m <= 1.2
                else "1.2–1.5" if m <= 1.5 else "> 1.5")

    _ratio = (
        _p.with_columns(
            pl.col("role multiplier").map_elements(_band, return_dtype=pl.String).alias("Multiplier")
        )
        .group_by("Multiplier")
        .agg(
            pl.len().alias("Observations"),
            pl.col("role multiplier").mean().round(2).alias("Mean multiplier"),
            (pl.col("actual").sum() / pl.col("window").sum()).round(2).alias("Actual ÷ window"),
            pl.col("window").mean().round(1).alias("Window min"),
        )
        .sort("Mean multiplier")
    )
    mo.vstack(
        [
            mo.md(
                f"**Fitted:** trend half-life {_m.half_life} games, δ = {_m.delta}; combined "
                f"weights $\\beta_t$ = {_c.beta_trend:.2f}, $\\beta_r$ = {_c.beta_role:.2f} "
                f"with {_c.roles.k} roles."
            ),
            mo.md("**Minutes forecast**, error vs. the window average (no multiplier):"),
            mo.ui.table(roles.scores, selection=None, show_column_summaries=False),
            mo.md("**Stat projections**, error reduction from multiplying the window average "
                  "by each multiplier:"),
            mo.ui.table(roles.stat_scores, selection=None, show_column_summaries=False),
            mo.md("**Role shifts.** Where the last 5 games point to a different role than the "
                  "whole window. *Match* labels the next 15 games with the same mixture (minutes, "
                  "spread and usage) and checks which role they land in."),
            mo.ui.table(roles.shifts, selection=None, show_column_summaries=False),
            mo.md("**Which part of the role signal predicts?** *Level* is the minutes typical "
                  "of the role the player now seems to be in; *drift* is only the change from "
                  "the window's role. Drift adds nothing the trend doesn't already have: the "
                  "gain is reversion toward role levels."),
            mo.ui.table(roles.components, selection=None, show_column_summaries=False),
            mo.md("**Bias by window minutes** (mean forecast − actual, minutes). The trend alone "
                  "over-predicts heavy-minute players; role levels correct most of it and slightly "
                  "over-correct the top band."),
            mo.ui.table(roles.bias, selection=None, show_column_summaries=False),
            mo.hstack([_grid, _cal], widths=[1, 1]),
            mo.md(
                f"""
    **By multiplier.** In the middle the multiplier matches what happened. At the extremes it
    overshoots: the strongest penalties were followed by smaller drops than predicted, and the
    strongest boosts by bigger rises. These are mostly low-minute players (see *Window min*),
    where ratios swing widely. A monotone recalibration didn't reduce minutes error, so it isn't
    applied. Separate trend weights for drops and rises (β = {symmetry["down"]:.2f} and
    {symmetry["up"]:.2f}) didn't either: CV MSE {symmetry["mse_split"]:.2f} vs.
    {symmetry["mse_one"]:.2f} with one weight.
    """
            ),
            mo.ui.table(_ratio, selection=None, show_column_summaries=False),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 5. Multipliers now

    The fitted model at the as-of date, for players with 5+ games. Early in a season, a few
    games carry the signal: last season's games still count, at weight δ.
    """)
    return


@app.cell
def _(
    as_of,
    engine,
    from_snapshot,
    get_league,
    league_picker,
    logs,
    mn,
    names,
    np,
    pl,
    result,
    roles,
):
    with engine.connect() as _conn:
        _snap = get_league(_conn, league_picker.value)
    _owner = from_snapshot(_snap).owner
    _teams = {t.fantasy_team_id: t.name for t in _snap.teams}
    _cut = mn.cut_after(as_of.value)
    _now = logs.season_of(np.array([_cut]))[0]
    _pids = [
        p for p, d in logs.dates.items()
        if np.searchsorted(d, _cut) >= 5 and logs.season_of(d[-1:])[0] >= _now - 1
    ]
    _f = mn.features(logs, [(p, _cut) for p in _pids])
    _model = roles.model
    _fc, _m = _model.forecast(_f), _model.multiplier(_f)
    _m_trend = result.model.multiplier(_f)
    _rm = _model.roles
    _window_role = _rm.label(_f.minutes[:, : mn.WINDOW], _f.poss[:, : mn.WINDOW])
    _post = _rm.posterior(_f, result.model.delta)
    _rows = []
    for _i, _pid in enumerate(_pids):
        _this = ~_f.earlier[_i] & ~np.isnan(_f.minutes[_i])
        _now_role = int(_post[_i].argmax())
        _rows.append(
            {
                "Player": names.get(_pid, str(_pid)),
                "Fantasy team": _teams[_owner[_pid]] if _pid in _owner else "Free agent",
                "Window min": round(float(_f.window[_i, 0]), 1),
                "This season": (
                    f"{float(np.nanmean(_f.minutes[_i][_this])):.1f} ({int(_this.sum())} g)"
                    if _this.any() else "–"
                ),
                "Window role": _rm.names[_window_role[_i]],
                "Role now": f"{_rm.names[_now_role]} {_post[_i, _now_role]:.0%}",
                "Forecast min": round(float(_fc[_i]), 1),
                "Multiplier": round(float(_m[_i]), 2),
                "Trend only": round(float(_m_trend[_i]), 2),
                "Last 5": " ".join(f"{x:.0f}" for x in _f.minutes[_i, :5] if not np.isnan(x)),
            }
        )
    current = pl.DataFrame(_rows)
    return (current,)


@app.cell
def _(mo):
    pool = mo.ui.radio(
        options=["Rostered + free agents", "Rostered", "Free agents", "Everyone"],
        value="Rostered + free agents",
        label="Players",
        inline=True,
    )
    min_window = mo.ui.slider(0, 30, value=10, step=1, label="Min window minutes",
                              show_value=True)
    mo.hstack([pool, min_window], justify="start")
    return min_window, pool


@app.cell
def _(current, min_window, mo, pl, pool):
    _c = current.filter(pl.col("Window min") >= min_window.value)
    if pool.value == "Rostered":
        _c = _c.filter(pl.col("Fantasy team") != "Free agent")
    elif pool.value == "Free agents":
        _c = _c.filter(pl.col("Fantasy team") == "Free agent")
    elif pool.value == "Rostered + free agents":
        # Free agents only matter if they're plausible pickups: 10+ forecast minutes.
        _c = _c.filter((pl.col("Fantasy team") != "Free agent") | (pl.col("Forecast min") >= 10))
    _shifted = _c.filter(pl.col("Window role") != pl.col("Role now").str.replace(r" \d+%$", ""))
    mo.vstack(
        [
            mo.md("**Biggest penalties** (falling minutes):"),
            mo.ui.table(_c.sort("Multiplier").head(15), selection=None,
                        show_column_summaries=False),
            mo.md("**Biggest boosts** (rising minutes):"),
            mo.ui.table(_c.sort("Multiplier", descending=True).head(15), selection=None,
                        show_column_summaries=False),
            mo.md(f"**Role shifts flagged** ({_shifted.height}): the last 5 games point to a "
                  "different role than the window."),
            mo.ui.table(_shifted.sort("Multiplier"), selection=None, page_size=15,
                        show_column_summaries=False),
        ]
    )
    return


@app.cell
def _(current, mo):
    lookup = mo.ui.multiselect(
        options=sorted(current["Player"].unique().to_list()),
        value=[n for n in ("Kyle Filipowski", "Brice Sensabaugh") if n in set(current["Player"])],
        label="Look up players",
    )
    return (lookup,)


@app.cell
def _(current, lookup, mo, pl):
    mo.vstack(
        [
            lookup,
            mo.ui.table(current.filter(pl.col("Player").is_in(lookup.value)), selection=None,
                        show_column_summaries=False),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 6. Caveats and next steps

    - **Roles are a convenient grid on a continuum**, not discrete types. The role model helps by
      pulling minutes toward each role's typical level (reversion), not by detecting jumps
      between crisp categories; that drift is already in the trend.
    - **Heavy-minute players are pulled down a little too far** (about 0.8 minutes for 33+
      minute players, section 4), so a star's multiplier sits slightly below 1 even with no
      change in role.
    - **Extremes overshoot** for low-minute players (section 4). For a rostered player the
      multiplier is usually in the well-calibrated middle.
    - **Two games is a thin signal.** Early in a season the model leans on last season (weight
      δ) and on weights fit on past seasons' early weeks, but one blowout can still move it.
    - **No starter flag.** The box scores loaded don't say who started, so "starter" and "role
      player" are minutes-and-usage profiles: a high-usage sixth man reads as a starter, a
      low-usage starter as a role player. A starts signal would sharpen them.
    - **Usage defines roles but isn't forecast.** The multiplier scales minutes only. A player
      can keep their minutes while their shots drop (a new star arrives); a usage trend would be
      the natural next factor.
    - **Not yet in the rankings.** Feeding it in means scaling counting stats by $m_i$ in the
      rankings notebook's (xLift) projections, a separate step kept apart on purpose.
    """)
    return


if __name__ == "__main__":
    app.run()
