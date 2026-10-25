import marimo

__generated_with = "0.25.2"
app = marimo.App(
    width="medium",
    app_title="Category Wins Added",
    auto_download=["html"],
)


@app.cell
def _():
    import warnings
    from datetime import date
    from statistics import NormalDist

    import altair as alt
    import marimo as mo
    import numpy as np
    import polars as pl

    import availability as av
    from ffmodel.contract.db import get_engine
    from ffmodel.core.data import (
        get_free_agents,
        get_league,
        get_player_details,
        list_leagues,
    )
    from ffmodel.core.model import build_prior, build_projections, shrink_projection
    from ffmodel.core.scenario import from_snapshot
    from ffmodel.core.scoring import get_format
    from ffmodel.core.sim import category_values, simulate_team, strategic_k

    return (
        NormalDist,
        alt,
        av,
        build_prior,
        build_projections,
        category_values,
        date,
        from_snapshot,
        get_engine,
        get_format,
        get_free_agents,
        get_league,
        get_player_details,
        list_leagues,
        mo,
        np,
        pl,
        shrink_projection,
        simulate_team,
        strategic_k,
        warnings,
    )


@app.cell
def _(mo):
    mo.md(r"""
    # Expected Weekly Category Wins Added (xWCWA)

    Standings Gain Points (SGP) asks: *how many units of a stat does it take to move up one
    place in the standings?* A player is worth their stats divided by those per-place costs.

    Classic SGP uses **one** cost per category, a straight line through the standings. This
    report tests a hypothesis about our league: **the cost of a rank depends on where you are in
    the table.** Some places sit in a tight cluster (cheap to pass), others behind a big gap
    (expensive). If that's true, a player's value should be measured by what they actually gain
    from your team's position. That's the score at the end: **Expected Weekly Category Wins
    Added (xWCWA)**, the extra category wins per week a player adds across the league when they
    replace an average rostered player.

    All values are per scoring period, the same expected totals the Impact Analysis
    simulation is built on.

    **Notation.** Teams $t, u$ (there are $N$), players $i, j$, categories $c$, base stats $s$.
    A player's per-game projection is $\hat\mu_i$ (section 0), their availability is $a_i$, the
    expected share of games they play (section 0b), and $G$ is games per period. Then

    $$\ell_i = \hat\mu_i \, a_i \, G \qquad T_t = \sum_{i \,\in\, \text{active}(t)} \ell_i$$

    are a player's per-period line and a team's per-period totals. Category values come from
    totals: a counting category is its stat, $\text{PTS} = 2\,\text{FGM} + \text{3PM} +
    \text{FTM}$, and $\text{FG\%} = \text{FGM}/\text{FGA}$ (likewise FT%). Every comparison
    uses the **key**

    $$k_c(T) = d_c \, v_c(T), \qquad d_c = -1 \text{ for TO}, \; +1 \text{ otherwise},$$

    so larger is always better. Write $k_{tc} = k_c(T_t)$. Tables show FG% and FT% in
    percentage points.
    """)
    return


@app.cell
def _(get_engine, list_leagues, mo):
    engine = get_engine()
    with engine.connect() as _conn:
        _leagues = list_leagues(_conn)
    league_picker = mo.ui.dropdown(
        {l.name: l.league_id for l in _leagues}, value=_leagues[0].name, label="League"
    )
    return engine, league_picker


@app.cell
def _(date, engine, from_snapshot, get_league, league_picker, mo):
    with engine.connect() as _conn:
        snapshot = get_league(_conn, league_picker.value)
    scenario = from_snapshot(snapshot)
    team_names = {t.fantasy_team_id: t.name for t in snapshot.teams}
    team_picker = mo.ui.dropdown(
        {name: tid for tid, name in team_names.items()},
        value=next(iter(team_names.values())),
        label="Your team",
    )
    window = mo.ui.slider(5, 82, value=82, step=1, label="Games window", show_value=True)
    games_per_period = mo.ui.slider(
        1, 4, value=3, step=1, label="Games per period", show_value=True
    )
    as_of = mo.ui.date(value=date.today(), label="As of")
    shrink = mo.ui.switch(value=True, label="Shrink noisy projections")
    avail_mode = mo.ui.dropdown(
        ["dAB × tag", "Window (current model)"],
        value="dAB × tag",
        label="Availability",
    )
    mo.hstack(
        [league_picker, team_picker, window, games_per_period, as_of, shrink, avail_mode],
        wrap=True,
    )
    return (
        as_of,
        avail_mode,
        games_per_period,
        scenario,
        shrink,
        snapshot,
        team_names,
        team_picker,
        window,
    )


@app.cell
def _(
    as_of,
    build_prior,
    build_projections,
    engine,
    get_format,
    get_free_agents,
    get_player_details,
    scenario,
    snapshot,
    window,
):
    fmt = get_format(snapshot.settings.scoring_format_id)
    cats = fmt.categories
    stats = fmt.base_stats
    with engine.connect() as _conn:
        free_agents = get_free_agents(_conn, snapshot.settings.league_id)
        _rostered = [s.player_id for spots in scenario.rosters.values() for s in spots]
        # Raw window fits; the shrinkage below is applied (or not) by the switch.
        projections = build_projections(
            _conn,
            _rostered + [p.player_id for p in free_agents],
            fmt,
            window=window.value,
            as_of=as_of.value,
            prior=None,
        )
        # The same prior Impact Analysis shrinks toward.
        stat_prior = build_prior(_conn, fmt, window=window.value, as_of=as_of.value)
        _details = get_player_details(_conn, player_ids=list(projections))
    player_names = {pid: summary.full_name for pid, (summary, _status) in _details.items()}
    player_status = {pid: status for pid, (_summary, status) in _details.items()}
    return (
        cats,
        fmt,
        free_agents,
        player_names,
        player_status,
        projections,
        stat_prior,
        stats,
    )


@app.cell
def _(mo):
    mo.md(r"""
    ## 0. Projections, with the noise taken out

    A 15-game average is part skill, part luck. Luck is worst where samples are small: a
    reserve's free throws, a guard's steals. Ranking on raw averages over-credits hot streaks,
    and the best-looking free agents are the most likely to be hot. So each projection is
    shrunk toward the typical player by how much of it is noise (empirical Bayes):

    **Counting stats** (per game). Let $\bar\mu_i$ be player $i$'s window average over $n_i$
    games and $\text{se}_{is}$ its standard error (from the projection's covariance,
    $\sqrt{\Sigma_{i,ss}/n_i}$). Over the pool $P$ of every player with a game in the past year
    and at least 5 games in the window (the same prior Impact Analysis uses):

    $$m_s = \operatorname{mean}_{j \in P} \bar\mu_{js} \qquad
    \tau_s^2 = \operatorname{Var}_{j \in P}(\bar\mu_{js}) - \operatorname{mean}_{j \in P}
    \text{se}_{js}^2$$

    $$w_{is} = \frac{\tau_s^2}{\tau_s^2 + \text{se}_{is}^2} \qquad
    \hat\mu_{is} = m_s + w_{is}\,(\bar\mu_{is} - m_s)$$

    $\tau_s^2$ is the spread between players that isn't sampling error. The table's *real share
    of spread* is $\tau_s^2 / \operatorname{Var}(\bar\mu_s)$.

    **Percentages** (beta-binomial). With window makes $M_i = n_i \bar\mu_{i,\text{made}}$
    and attempts $A_i = n_i \bar\mu_{i,\text{att}}$, and $p_j = M_j / A_j$ over pool players
    with $A_j \ge 10$:

    $$\bar p = \frac{\sum_j M_j}{\sum_j A_j} \qquad
    \tau_p^2 = \operatorname{Var}(p_j) - \operatorname{mean}\!\left(\frac{p_j(1-p_j)}{A_j}\right)
    \qquad \kappa = \frac{\bar p(1-\bar p)}{\tau_p^2} - 1$$

    $$\hat p_i = \frac{M_i + \kappa\,\bar p}{A_i + \kappa} \qquad
    \hat\mu_{i,\text{made}} = \hat p_i \, \hat\mu_{i,\text{att}}$$

    $\kappa$ is the prior's weight in attempts (*worth k attempts* in the table). Attempts are
    shrunk as counting stats first, and 3PM is capped at FGM.
    """)
    return


@app.cell
def _(cats, pl, projections, shrink, shrink_projection, stat_prior, stats):
    means = {
        pid: (shrink_projection(p, stat_prior) if shrink.value else p).mean
        for pid, p in projections.items()
        if p.games_found > 0  # no projection: these players are left out
    }
    _labels = {
        (stats.index(c.numerator), stats.index(c.denominator)): c.label
        for c in cats
        if c.kind == "ratio"
    }
    _rows = (
        [
            {
                "Stat": _s.upper(),
                "Real share of spread": round(float(stat_prior.real_share[_i]), 2),
                "Prior": f"{stat_prior.mean[_i]:.2f} per game",
            }
            for _i, _s in enumerate(stats)
        ]
        + [
            {
                "Stat": _labels.get((_r.made, _r.attempts), "ratio"),
                "Real share of spread": round(_r.real_share, 2),
                "Prior": f"{100 * _r.rate:.1f}%, worth {_r.kappa:.0f} attempts",
            }
            for _r in stat_prior.ratios
        ]
        if stat_prior is not None
        else []
    )
    shrink_table = pl.DataFrame(_rows)
    return means, shrink_table


@app.cell
def _(mo, shrink_table):
    mo.ui.table(shrink_table, selection=None, show_column_summaries=False)
    return


@app.cell
def _(as_of, av, avail_mode, engine, means, mo, player_status, projections):
    # dAB, the backtested availability model from the Player Availability report.
    _data = av.load(engine, as_of.value)
    avail_fit = av.fit(av.backtest(_data)).fit
    _cut = av.cut_after(as_of.value)
    availability = {}
    for _pid in means:
        if avail_mode.value == "dAB × tag":
            _blend = avail_fit.blend(_data.counts(_pid, _cut))[0]
            availability[_pid] = _blend * av.tag_multiplier(player_status.get(_pid))
        else:
            availability[_pid] = projections[_pid].availability or 0.0
    mo.md(
        f"""
    ## 0b. Availability

    A player's per-period line scales with availability $a_i$ (games played ÷ games
    available). *dAB × tag* uses **dAB** (Decay-weighted Availability Blend), the backtested
    model from the Player Availability report: a blend of the recent window and a three-season
    rate, with older seasons weighted δ = {avail_fit.delta} per season of age, scaled by the
    platform's injury tag. *Window* is the
    app's current estimate. The report has the analysis, the backtest and the tuning.
    """
    )
    return (availability,)


@app.cell
def _(availability, games_per_period, means, np, scenario, stats):
    # Expected per-period line: per-game projection × availability × games per period.
    lines = {pid: m * availability[pid] * games_per_period.value for pid, m in means.items()}
    team_ids = sorted(scenario.rosters)
    team_totals = np.array(
        [
            sum((lines[p] for p in scenario.active_players(t) if p in lines), np.zeros(len(stats)))
            for t in team_ids
        ]
    )
    # The swap baseline: the average active rostered player.
    avg_line = np.mean(
        [lines[p] for t in team_ids for p in scenario.active_players(t) if p in lines], axis=0
    )
    return avg_line, lines, team_ids, team_totals


@app.cell
def _(cats, fmt, np, stats):
    # Ratio categories are shown in percentage points so gaps read naturally.
    SCALE = np.array([100.0 if c.kind == "ratio" else 1.0 for c in cats])
    UNIT = {c.label: ("pct pts" if c.kind == "ratio" else c.label) for c in cats}
    LABELS = [c.label for c in cats]

    def to_values(totals):
        """Base-stat totals (..., stats) → category values (..., categories)."""
        _d = {s: totals[..., i] for i, s in enumerate(stats)}
        for _name, _fn in fmt.derived_stats.items():
            _d[_name] = _fn(_d)
        return fmt.category_values(_d)

    def to_keys(totals):
        """Category values with direction applied: larger is always better (TO flipped)."""
        return fmt.rank_key(to_values(totals))

    return LABELS, SCALE, UNIT, to_keys, to_values


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. The league's shape

    Each dot is a team's projected per-period value, ordered by rank. Even spacing would mean
    every place costs the same; clusters and cliffs are where the hypothesis lives.
    """)
    return


@app.cell
def _(
    LABELS,
    SCALE,
    np,
    pl,
    team_ids,
    team_names,
    team_totals,
    to_keys,
    to_values,
):
    team_keys = to_keys(team_totals)  # (teams, categories)
    _vals = to_values(team_totals) * SCALE
    _order = np.argsort(-team_keys, axis=0, kind="stable")
    team_rank = np.empty_like(_order)
    for _c in range(team_keys.shape[1]):
        team_rank[_order[:, _c], _c] = np.arange(1, len(team_ids) + 1)
    ladder = pl.DataFrame(
        [
            {
                "team": team_names[t],
                "team_id": t,
                "category": LABELS[c],
                "value": float(_vals[i, c]),
                "rank": int(team_rank[i, c]),
            }
            for i, t in enumerate(team_ids)
            for c in range(len(LABELS))
        ]
    )
    return ladder, team_keys, team_rank


@app.cell
def _(LABELS, alt, ladder, team_names, team_picker):
    _mine = team_names[team_picker.value]
    _base = alt.Chart(ladder).encode(
        x=alt.X("rank:Q", title="Rank", scale=alt.Scale(domain=[1, 18], nice=False)),
        y=alt.Y("value:Q", title=None, scale=alt.Scale(zero=False)),
        tooltip=["team", "rank", alt.Tooltip("value:Q", format=".2f")],
    )
    _chart = (
        alt.layer(
            _base.mark_line(color="#9aa4b2", strokeWidth=1),
            _base.mark_circle(size=55).encode(
                color=alt.condition(
                    alt.datum.team == _mine, alt.value("#e4572e"), alt.value("#3b6ea8")
                )
            ),
        )
        .properties(width=210, height=150)
        .facet(facet=alt.Facet("category:N", sort=LABELS, title=None), columns=3)
        .resolve_scale(y="independent")
    )
    _chart
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. What a rank costs

    **Gap to reach rank *r*** = the units a team at rank *r*+1 needs to pass the team at rank
    *r*. With category $c$'s keys sorted best first, $k_{(1)} \ge k_{(2)} \ge \dots \ge
    k_{(N)}$:

    $$g_{c,r} = k_{(r)} - k_{(r+1)}, \qquad r = 1, \dots, N-1$$

    The heatmap shows $g_{c,r} / \operatorname{median}_r\, g_{c,r}$, so 1.0 is a typical step
    (white). Orange is an expensive step and blue a cheap one.
    """)
    return


@app.cell
def _(LABELS, NormalDist, SCALE, np, pl, team_keys):
    _n = team_keys.shape[0]
    # Null model: gaps between 18 draws from a normal with this category's spread (Blom's
    # approximation to expected normal order statistics). Bell-shaped leagues have wider gaps at
    # the extremes by geometry alone, so "the top is expensive" only counts beyond this.
    _z = np.array([NormalDist().inv_cdf((i - 0.375) / (_n + 0.25)) for i in range(_n, 0, -1)])
    _null_steps = _z[:-1] - _z[1:]
    _rows = []
    for _c, _label in enumerate(LABELS):
        _sorted = np.sort(team_keys[:, _c])[::-1] * SCALE[_c]
        _gaps = _sorted[:-1] - _sorted[1:]
        _null = _null_steps * np.std(_sorted, ddof=1)
        _med = float(np.median(_gaps)) or 1e-9
        for _r in range(_n - 1):
            _rows.append(
                {
                    "category": _label,
                    "to_rank": _r + 1,
                    "gap": float(_gaps[_r]),
                    "null_gap": float(_null[_r]),
                    "relative": float(_gaps[_r] / _med),
                }
            )
    gaps = pl.DataFrame(_rows)

    # The same comparison as a distribution: 20k simulated normal leagues of this size. The
    # band ratios don't depend on scale, so standard normals serve every category.
    _sims = -np.sort(-np.random.default_rng(0).standard_normal((20_000, _n)), axis=1)
    _sg = _sims[:, :-1] - _sims[:, 1:]
    _mid = _sg[:, 6:11].mean(axis=1)
    null_ratios = {"top": _sg[:, 0:3].mean(axis=1) / _mid, "bottom": _sg[:, 14:17].mean(axis=1) / _mid}
    return gaps, null_ratios


@app.cell
def _(LABELS, alt, gaps):
    alt.Chart(gaps).mark_rect().encode(
        x=alt.X("to_rank:O", title="Gap to reach rank"),
        y=alt.Y("category:N", sort=LABELS, title=None),
        color=alt.Color(
            "relative:Q",
            title="× median gap",
            scale=alt.Scale(type="log", scheme="blueorange", domainMid=1, clamp=True,
                            domain=[0.125, 8]),
        ),
        tooltip=[
            "category",
            "to_rank",
            alt.Tooltip("gap:Q", format=".2f", title="gap (units)"),
            alt.Tooltip("relative:Q", format=".2f", title="× median"),
        ],
    ).properties(width=620, height=260)
    return


@app.cell
def _(mo):
    mo.md(r"""
    **Against the null.** The grey line is the gap a normally-spread league of 18 teams with the
    same spread would show on average. Where the blue bars clear the grey line, that step is
    harder than geometry alone explains. It uses Blom's approximation to the expected normal
    order statistics, scaled by the sample SD $s_c$ of the teams' values:

    $$z_r = \Phi^{-1}\!\left(\frac{N - r + 1 - 0.375}{N + 0.25}\right) \qquad
    g^{\text{null}}_{c,r} = s_c\,(z_r - z_{r+1})$$

    The shape summary below compares bands of steps, top (into ranks 1–3), middle (7–11) and
    bottom (15–17):

    $$\text{Top} = \frac{\operatorname{mean}(g_{c,1..3})}{\operatorname{mean}(g_{c,7..11})}
    \qquad \text{Bottom} = \frac{\operatorname{mean}(g_{c,15..17})}{\operatorname{mean}(g_{c,7..11})}$$

    *Pctile* is the share of 20,000 simulated leagues of $N$ standard-normal teams whose ratio is
    lower. *Weekly SD* $\sigma_c$ is the median, over teams, of the standard deviation of the
    team's simulated per-period value (each player plays $\text{Binomial}(G, a_i)$ games), and
    *Gap ÷ weekly SD* is $\operatorname{median}_r g_{c,r} / \sigma_c$.
    """)
    return


@app.cell
def _(LABELS, alt, gaps):
    _base = alt.Chart(gaps).encode(x=alt.X("to_rank:O", title="Gap to reach rank"))
    (
        alt.layer(
            _base.mark_bar(color="#3b6ea8", opacity=0.8).encode(
                y=alt.Y("gap:Q", title="units"),
                tooltip=[
                    "to_rank",
                    alt.Tooltip("gap:Q", format=".2f"),
                    alt.Tooltip("null_gap:Q", format=".2f", title="null"),
                ],
            ),
            _base.mark_line(color="#6b7280", point=True).encode(y="null_gap:Q"),
        )
        .properties(width=210, height=140)
        .facet(facet=alt.Facet("category:N", sort=LABELS, title=None), columns=3)
        .resolve_scale(y="independent")
    )
    return


@app.cell
def _(
    SCALE,
    category_values,
    fmt,
    games_per_period,
    np,
    projections,
    scenario,
    simulate_team,
    strategic_k,
    team_ids,
):
    # Weekly noise: each team's simulated per-period spread, median over teams. A gap well under
    # this is inside the noise of a single H2H week.
    _sds = []
    for _t in team_ids:
        _samples = simulate_team(
            _t,
            [projections[p] for p in scenario.active_players(_t) if p in projections],
            strategic_k(games_per_period.value),
            fmt,
            iterations=4000,
            seed=20261024,
            mode_code=1,
        )
        _sds.append(np.nanstd(category_values(_samples, fmt), axis=0))
    weekly_sd = np.median(np.array(_sds), axis=0) * SCALE
    return (weekly_sd,)


@app.cell
def _(LABELS, UNIT, gaps, mo, np, null_ratios, pl, weekly_sd):
    def _band(df, lo, hi):
        return df.filter((pl.col("to_rank") >= lo) & (pl.col("to_rank") <= hi))["gap"].mean()

    def _pctile(ratio, null):
        return int(round(100 * float(np.mean(null < ratio))))

    _rows = []
    for _c, _label in enumerate(LABELS):
        _g = gaps.filter(pl.col("category") == _label)
        _mid = _band(_g, 7, 11)
        _top, _bot = _band(_g, 1, 3) / _mid, _band(_g, 15, 17) / _mid
        _rows.append(
            {
                "Category": _label,
                "Unit": UNIT[_label],
                "Median gap": round(float(_g["gap"].median()), 2),
                "Weekly SD": round(float(weekly_sd[_c]), 2),
                "Gap ÷ weekly SD": round(float(_g["gap"].median() / weekly_sd[_c]), 2),
                "Top ÷ middle": round(_top, 2),
                "Top pctile": _pctile(_top, null_ratios["top"]),
                "Bottom ÷ middle": round(_bot, 2),
                "Bottom pctile": _pctile(_bot, null_ratios["bottom"]),
            }
        )
    shape_summary = pl.DataFrame(_rows)
    mo.vstack(
        [
            mo.md(
                "**Shape summary.** *Top* = steps into ranks 1–3, *middle* = 7–11, *bottom* = "
                "15–17. *Pctile* places each ratio among 20,000 simulated normal leagues of the "
                f"same size, where a typical *Top ÷ middle* is already "
                f"{np.median(null_ratios['top']):.1f}. *Gap ÷ weekly SD* under ~0.2 means one "
                "rank is small next to a single week's noise."
            ),
            mo.ui.table(shape_summary, selection=None, show_column_summaries=False),
        ]
    )
    return (shape_summary,)


@app.cell
def _(mo, pl, shape_summary):
    # Verdict per tail: steeper than 95% of simulated normal leagues. With 9 categories × 2 tails,
    # about one of the 18 checks clears that bar by chance alone.
    _s = shape_summary
    _top = _s.filter(pl.col("Top pctile") >= 95)["Category"].to_list()
    _bot = _s.filter(pl.col("Bottom pctile") >= 95)["Category"].to_list()
    _flat = _s.filter((pl.col("Top pctile") <= 25) & (pl.col("Bottom pctile") <= 25))[
        "Category"
    ].to_list()
    _hits = len(_top) + len(_bot)

    def _list(xs):
        return ", ".join(xs) if xs else "none"

    if _hits >= 3:
        _lead = (
            f"{_hits} of 18 tails are steeper than 95% of normal leagues, where chance alone "
            "gives about one. This league has cliffs of its own, on top of the usual geometry."
        )
    elif _hits:
        _lead = (
            f"Only {_hits} of 18 tails are steeper than 95% of normal leagues, about what chance "
            "gives. The league's shape is mostly the usual geometry."
        )
    else:
        _lead = "No tail is steeper than 95% of normal leagues: the shape is the usual geometry."

    mo.callout(
        mo.md(f"""
    **What this shows.** {_lead} Either way the cost of a rank is not constant (in any
    bell-shaped league the top steps cost about twice the middle ones), which is the case for
    weighting by position.

    - **Expensive top** (≥95th pctile): {_list(_top)}.
    - **Expensive bottom** (≥95th pctile, hard to climb out of last): {_list(_bot)}.
    - **Flatter than a normal league** at both ends (≤25th pctile): {_list(_flat)}.
    - A typical one-rank step is **{_s["Gap ÷ weekly SD"].min():.2f}–{_s["Gap ÷ weekly SD"].max():.2f}
      weekly SDs**. Ranks describe season-long strength; in any single H2H week they are
      mostly noise.
    """),
        kind="info",
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. What the waiver wire can buy

    The other half of difficulty is supply. For each category, take the free agents' marginal
    effect when one replaces an average rostered player on an average team, and average the ten
    best. **Pickups per rank** is the gap divided by that: how many top waiver adds a single step
    costs. With the average team $\bar T = \operatorname{mean}_t T_t$ and the average active
    rostered line $\bar\ell$:

    $$\Delta_{ic} = k_c(\bar T - \bar\ell + \ell_i) - k_c(\bar T) \qquad
    S_c = \operatorname{mean}\big(\text{top 10 of } \Delta_{ic} \text{ over free agents } i\big)$$

    $$\text{Pickups}_{c,r} = g_{c,r} / S_c$$
    """)
    return


@app.cell
def _(
    LABELS,
    SCALE,
    avg_line,
    free_agents,
    gaps,
    lines,
    np,
    pl,
    team_totals,
    to_keys,
):
    _fa_ids = [p.player_id for p in free_agents if p.player_id in lines]
    _avg_team = team_totals.mean(axis=0)
    _fa_lines = np.array([lines[p] for p in _fa_ids])
    _delta = (to_keys(_avg_team - avg_line + _fa_lines) - to_keys(_avg_team)) * SCALE
    fa_supply = np.array(
        [np.mean(np.sort(_delta[:, c])[::-1][:10]) for c in range(len(LABELS))]
    )
    supply = gaps.with_columns(
        pl.col("category")
        .replace_strict(dict(zip(LABELS, fa_supply.tolist())))
        .alias("supply")
    ).with_columns((pl.col("gap") / pl.col("supply")).alias("pickups"))
    return (supply,)


@app.cell
def _(LABELS, alt, supply):
    alt.Chart(supply).mark_rect().encode(
        x=alt.X("to_rank:O", title="Gap to reach rank"),
        y=alt.Y("category:N", sort=LABELS, title=None),
        color=alt.Color(
            "pickups:Q",
            title="Pickups per rank",
            scale=alt.Scale(type="sqrt", scheme="oranges"),
        ),
        tooltip=[
            "category",
            "to_rank",
            alt.Tooltip("gap:Q", format=".2f"),
            alt.Tooltip("supply:Q", format=".2f", title="top-10 FA gain"),
            alt.Tooltip("pickups:Q", format=".2f"),
        ],
    ).properties(width=620, height=260)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 4. xWCWA: category wins added, from your position

    For an evaluating team, each category becomes a **rank curve**, and a player's value is how
    far they move the team along it. *Rank curve* picks one of two:

    - **Weekly win odds** (the default, for H2H). A team's rank is 1 + the expected number of
      other teams that beat it in that category in a given week, using the category's weekly
      noise. Gaining one rank means winning that category against one more opponent per week,
      on average. Noisy categories pay less per unit, because an edge there flips less often.
      Edges keep paying past first place, at a falling rate.
      Summed over categories, the gain is **xWCWA**: expected extra category wins per week
      across all 17 opponents. Divide by 17 for the gain in a single matchup.
    - **Season ranks**. The other 17 teams' values are knots, and passing one gains a full
      rank. A unit in a tight cluster buys several ranks, a unit behind a cliff buys a fraction,
      and a unit past first place buys nothing. With this curve the same score counts
      standings places gained rather than weekly wins.

    A player's xWCWA for a team is the gain across all nine categories when they come in
    for someone (ratio categories are recomputed from the new makes and attempts). *Swap out*
    picks who leaves: an **average rostered player**, or the team's own **weakest player**, the
    one whose removal costs the fewest ranks. **League xWCWA** averages that over every team
    except their own, a position-neutral value. **Flat SGP** is the classic version, using one
    per-rank cost per category (the slope of value against rank), for comparison.

    **Rank curves.** For team $t$ in category $c$, as a function of a key value $x$:

    *Weekly win odds*, with $\Phi$ the standard normal CDF and $\sigma_c$ the weekly SD
    (section 2). Two teams' values differ by noise of $\sqrt2\,\sigma_c$:

    $$R_{tc}(x) = 1 + \sum_{u \ne t} \Phi\!\left(\frac{k_{uc} - x}{\sqrt2\,\sigma_c}\right)$$

    *Season ranks*. Sort the other teams' keys best first, $k^{-t}_{(1)} \ge \dots \ge
    k^{-t}_{(N-1)}$. $R_{tc}$ is the piecewise-linear interpolation through the knots

    $$\big(k^{-t}_{(j)},\ j\big)_{j=1}^{N-1} \quad\text{and}\quad
    \big(k^{-t}_{(N-1)} - \tilde g,\ N\big),$$

    with $\tilde g$ the median gap between the other teams. It is held at 1 above the best and
    at $N$ below the last knot.

    **Swap.** Player $i$ replaces line $\ell_{o_t}$ on team $t$:

    $$k'_{tic} = k_c\big(T_t - \ell_{o_t} + \ell_i\big)$$

    $\ell_{o_t} = \bar\ell$ for the average player. For the weakest player, it is the active
    player whose removal loses the fewest ranks (zero if an active player has no projection):

    $$o_t = \arg\min_{j \,\in\, \text{active}(t)}
    \sum_c \Big[R_{tc}\big(k_c(T_t - \ell_j)\big) - R_{tc}(k_{tc})\Big]$$

    **Scores.**

    $$\text{xWCWA}_{ti} = \sum_c \Big[R_{tc}(k_{tc}) - R_{tc}(k'_{tic})\Big] \qquad
    \text{xWCWA}_i = \operatorname{mean}_{t \,\ne\, \text{owner}(i)} \text{xWCWA}_{ti}$$

    For flat SGP, fit $k_{(r)} \approx \alpha_c + \beta_c\, r$ by least squares over all $N$
    teams. The cost of one rank is $D_c = -\beta_c$, and

    $$\text{Flat}_{ti} = \sum_c \frac{k'_{tic} - k_{tc}}{D_c},$$

    averaged over teams the same way. *Moved* = flat rank − xWCWA rank.
    """)
    return


@app.cell
def _(
    SCALE,
    avg_line,
    baseline,
    curve,
    lines,
    np,
    scenario,
    stats,
    team_ids,
    team_keys,
    team_totals,
    to_keys,
    weekly_sd,
):
    _n_teams, _n_cats = team_keys.shape
    player_ids = sorted(lines)
    _P = np.array([lines[p] for p in player_ids])
    _owner = scenario.owner

    # Rank curve per (team, category): the other teams' values are knots. Tying the k-th best
    # other team = rank k; one median gap below the worst = last.
    _knots = {}
    for _ti in range(_n_teams):
        for _c in range(_n_cats):
            _others = np.sort(np.delete(team_keys[:, _c], _ti))  # ascending
            _step = np.median(np.diff(_others))
            _knots[_ti, _c] = (
                np.concatenate([[_others[0] - _step], _others]),
                np.concatenate([[_n_teams], np.arange(_n_teams - 1, 0, -1)]),
            )

    # Weekly: two teams' totals differ by noise of √2 × one team's weekly SD (in key units).
    _diff_sd = np.sqrt(2) * weekly_sd / SCALE

    def _phi(x):
        """Standard normal CDF (Abramowitz–Stegun 7.1.26 erf, error < 2e-7)."""
        _z = np.abs(x) / np.sqrt(2)
        _t = 1 / (1 + 0.3275911 * _z)
        _poly = _t * (0.254829592 + _t * (-0.284496736 + _t * (1.421413741
                + _t * (-1.453152027 + _t * 1.061405429))))
        _erf = 1 - _poly * np.exp(-_z * _z)
        return 0.5 * (1 + np.sign(x) * _erf)

    def _rank(ti, c, v):
        if curve.value == "Weekly win odds":
            # 1 + the expected number of other teams that beat this one in a week.
            _o = np.delete(team_keys[:, c], ti)
            return 1 + _phi(np.subtract.outer(_o, np.asarray(v)) / _diff_sd[c]).sum(axis=0)
        return np.interp(v, *_knots[ti, c])

    # Who makes room: the league-average player, or the team's own weakest active player (the
    # one whose removal costs the fewest ranks; a player with no recent games costs none).
    if baseline.value == "Team's weakest player":
        _out = []
        for _ti, _t in enumerate(team_ids):
            _active = scenario.active_players(_t)
            if any(p not in lines for p in _active):
                _out.append(np.zeros(len(stats)))
                continue
            _L = np.array([lines[p] for p in _active])
            _without = to_keys(team_totals[_ti] - _L)  # (active, cats)
            _lost = sum(
                _rank(_ti, _c, _without[:, _c]) - _rank(_ti, _c, team_keys[_ti, _c])
                for _c in range(_n_cats)
            )
            _out.append(_L[np.argmin(_lost)])
        _out = np.array(_out)
    else:
        _out = np.broadcast_to(avg_line, team_totals.shape)
    _new = to_keys((team_totals - _out)[:, None, :] + _P[None, :, :])  # (teams, players, cats)

    rgp = np.full((_n_teams, len(player_ids), _n_cats), np.nan)
    flat = np.full_like(rgp, np.nan)
    for _c in range(_n_cats):
        # Classic SGP denominator: units per rank from a straight-line fit.
        _per_rank = -np.polyfit(
            np.arange(1, _n_teams + 1), np.sort(team_keys[:, _c])[::-1], 1
        )[0]
        for _ti in range(_n_teams):
            rgp[_ti, :, _c] = _rank(_ti, _c, team_keys[_ti, _c]) - _rank(_ti, _c, _new[_ti, :, _c])
            flat[_ti, :, _c] = (_new[_ti, :, _c] - team_keys[_ti, _c]) / _per_rank

    # A player's own team already has them: leave that evaluation out.
    for _pi, _p in enumerate(player_ids):
        if _p in _owner:
            _ti = team_ids.index(_owner[_p])
            rgp[_ti, _pi, :] = np.nan
            flat[_ti, _pi, :] = np.nan
    return flat, player_ids, rgp


@app.cell
def _(mo):
    scope = mo.ui.radio(
        options=["League (position-neutral)", "Your team"],
        value="League (position-neutral)",
        label="Evaluate for",
        inline=True,
    )
    pool = mo.ui.radio(
        options=["Free agents", "All players"], value="Free agents", label="Pool", inline=True
    )
    baseline = mo.ui.radio(
        options=["Average rostered player", "Team's weakest player"],
        value="Average rostered player",
        label="Swap out",
        inline=True,
    )
    curve = mo.ui.radio(
        options=["Weekly win odds", "Season ranks"],
        value="Weekly win odds",
        label="Rank curve",
        inline=True,
    )
    top_n = mo.ui.slider(10, 50, value=25, step=5, label="Show top", show_value=True)
    min_games = mo.ui.slider(1, 15, value=5, step=1, label="Min games", show_value=True)
    mo.hstack([scope, pool, baseline, curve, top_n, min_games], wrap=True, justify="start")
    return baseline, curve, min_games, pool, scope, top_n


@app.cell
def _(
    LABELS,
    flat,
    min_games,
    np,
    pl,
    player_ids,
    player_names,
    pool,
    projections,
    rgp,
    scenario,
    scope,
    team_ids,
    team_names,
    team_picker,
    warnings,
):
    with warnings.catch_warnings():
        # Mean of an all-NaN slice: a player evaluated by no team. Skipped below.
        warnings.simplefilter("ignore", RuntimeWarning)
        if scope.value == "Your team":
            _ti = team_ids.index(team_picker.value)
            _by_cat, _flat = rgp[_ti], flat[_ti].sum(axis=1)
        else:
            _by_cat, _flat = np.nanmean(rgp, axis=0), np.nanmean(flat, axis=0).sum(axis=1)
    _owner = scenario.owner
    _rows = []
    for _pi, _p in enumerate(player_ids):
        if np.isnan(_by_cat[_pi]).all():
            continue  # on the evaluating team already
        if pool.value == "Free agents" and _p in _owner:
            continue
        _proj = projections[_p]
        if _proj.games_found < min_games.value:
            continue  # a one- or two-game window is a raw stat line, not a projection
        _row = {
            "player_id": _p,
            "Player": player_names.get(_p, str(_p)),
            "Team": team_names[_owner[_p]] if _p in _owner else "Free agent",
            "xWCWA": float(np.sum(_by_cat[_pi])),
            "Flat SGP": float(_flat[_pi]),
            "Games": f"{_proj.games_found}/{_proj.games_requested}",
        }
        _row |= {_l: float(_by_cat[_pi, _c]) for _c, _l in enumerate(LABELS)}
        _rows.append(_row)
    board = (
        pl.DataFrame(_rows)
        .with_columns(
            pl.col("xWCWA").rank("ordinal", descending=True).alias("xWCWA rank"),
            pl.col("Flat SGP").rank("ordinal", descending=True).alias("Flat rank"),
        )
        .with_columns(
            (pl.col("Flat rank").cast(pl.Int64) - pl.col("xWCWA rank").cast(pl.Int64)).alias("Moved")
        )
        .sort("xWCWA", descending=True)
    )
    return (board,)


@app.cell
def _(LABELS, alt, board, top_n):
    _top = board.head(top_n.value)
    _long = _top.unpivot(index=["Player"], on=LABELS, variable_name="category", value_name="ranks")
    _order = _top["Player"].to_list()
    _bars = alt.Chart(_long).mark_bar().encode(
        y=alt.Y("Player:N", sort=_order, title=None),
        x=alt.X("ranks:Q", title="Ranks gained (stacked by category)"),
        color=alt.Color("category:N", sort=LABELS, scale=alt.Scale(scheme="tableau10")),
        tooltip=["Player", "category", alt.Tooltip("ranks:Q", format=".2f")],
    )
    _totals = alt.Chart(_top.select("Player", "xWCWA")).mark_tick(
        color="black", thickness=2, size=14
    ).encode(y=alt.Y("Player:N", sort=_order), x="xWCWA:Q")
    (_bars + _totals).properties(
        width=620, height=max(240, 18 * len(_order)), title="xWCWA leaderboard (tick = net xWCWA)"
    )
    return


@app.cell
def _(LABELS, board, mo, top_n):
    mo.ui.table(
        board.head(top_n.value).select(
            "xWCWA rank", "Player", "Team", "xWCWA", "Flat SGP", "Flat rank", "Moved", "Games",
            *LABELS,
        ),
        selection=None,
        format_mapping={c: "{:.2f}" for c in ["xWCWA", "Flat SGP", *LABELS]},
        show_column_summaries=False,
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    **Does the weighting matter?** Each dot is a player, placed by their rank under flat SGP and
    under xWCWA. Dots on the diagonal rank the same either way; distance from it is how much the
    league's shape reorders them.
    """)
    return


@app.cell
def _(alt, board, pl):
    _top = board.filter((pl.col("xWCWA rank") <= 100) | (pl.col("Flat rank") <= 100))
    _pts = alt.Chart(_top).mark_circle(size=40, opacity=0.7).encode(
        x=alt.X("Flat rank:Q", title="Flat SGP rank", scale=alt.Scale(domain=[0, 100])),
        y=alt.Y("xWCWA rank:Q", title="xWCWA rank", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color(
            "Moved:Q", scale=alt.Scale(scheme="redblue", domainMid=0), title="Places gained"
        ),
        tooltip=["Player", "Team", "xWCWA rank", "Flat rank", alt.Tooltip("xWCWA:Q", format=".2f")],
    )
    _diag = alt.Chart(pl.DataFrame({"x": [0, 100], "y": [0, 100]})).mark_line(
        color="#9aa4b2", strokeDash=[4, 4]
    ).encode(x="x:Q", y="y:Q")
    (_diag + _pts).properties(width=420, height=420).interactive()
    return


@app.cell
def _(
    flat,
    mo,
    np,
    player_ids,
    rgp,
    scenario,
    team_ids,
    team_names,
    team_picker,
):
    # How far the league's shape reorders free agents, for every team (Spearman of xWCWA vs flat).
    _fa = [i for i, p in enumerate(player_ids) if p not in scenario.owner]

    def _spearman(a, b):
        _ra, _rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b))
        return float(np.corrcoef(_ra, _rb)[0, 1])

    with np.errstate(all="ignore"):
        _league = _spearman(
            np.nanmean(rgp, axis=0)[_fa].sum(axis=1), np.nanmean(flat, axis=0)[_fa].sum(axis=1)
        )
    _by_team = [_spearman(rgp[t][_fa].sum(axis=1), flat[t][_fa].sum(axis=1)) for t in range(len(team_ids))]
    _top10 = {frozenset(np.argsort(-rgp[t][_fa].sum(axis=1))[:10]) for t in range(len(team_ids))}
    _mine = _by_team[team_ids.index(team_picker.value)]
    _low = int(np.argmin(_by_team))
    if _league >= 0.95 and min(_by_team) < 0.8:
        _read = (
            "Positions average out across the league, but from a single team's position the "
            "weighting reorders free agents a lot. xWCWA is most useful as a team-specific score: "
            "switch *Evaluate for* to *Your team* above."
        )
    elif min(_by_team) >= 0.9:
        _read = "Even from single teams' positions, the weighting changes little in this league."
    else:
        _read = "The weighting reorders free agents both league-wide and from single positions."
    mo.callout(
        mo.md(f"""
    **Where the weighting matters.** Rank correlation between xWCWA and flat SGP orders of free
    agents: **{_league:.2f}** averaged over the league, **{_mine:.2f}** for
    {team_names[team_picker.value]}, and lowest at **{_by_team[_low]:.2f}** for
    {team_names[team_ids[_low]]}. **{len(_top10)} of {len(team_ids)}** teams get a different
    top-10 free-agent list. {_read}
    """),
        kind="info",
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 5. Your team's ladder

    Where your team sits in each category, what the next step up costs, how much cushion you have
    over the team below, and the free agent who gains you the most ranks there:

    $$\text{To next rank} = \min_{u:\,k_{uc} > k_{tc}} k_{uc} - k_{tc} \qquad
    \text{Cushion} = k_{tc} - \max_{u:\,k_{uc} < k_{tc}} k_{uc}$$

    *FA ranks* is the best free agent's $R_{tc}(k_{tc}) - R_{tc}(k'_{tic})$ under the current
    *Rank curve* and *Swap out*.
    """)
    return


@app.cell
def _(
    LABELS,
    SCALE,
    UNIT,
    mo,
    pl,
    player_ids,
    player_names,
    rgp,
    scenario,
    team_ids,
    team_keys,
    team_picker,
    team_rank,
):
    _ti = team_ids.index(team_picker.value)
    # This team's own xWCWA for free agents, whatever the leaderboard toggles say.
    _fa = [i for i, p in enumerate(player_ids) if p not in scenario.owner]
    _rows = []
    for _c, _label in enumerate(LABELS):
        _mine = team_keys[_ti, _c]
        _col = team_keys[:, _c]
        _above = _col[_col > _mine]
        _below = _col[_col < _mine]
        _best = max(_fa, key=lambda i: rgp[_ti, i, _c]) if _fa else None
        _rows.append(
            {
                "Category": _label,
                "Rank": int(team_rank[_ti, _c]),
                "To next rank": (
                    round(float((_above.min() - _mine) * SCALE[_c]), 2) if _above.size else None
                ),
                "Cushion": (
                    round(float((_mine - _below.max()) * SCALE[_c]), 2) if _below.size else None
                ),
                "Unit": UNIT[_label],
                "Best FA here": player_names[player_ids[_best]] if _best is not None else None,
                "FA ranks": round(float(rgp[_ti, _best, _c]), 2) if _best is not None else None,
            }
        )
    mo.ui.table(pl.DataFrame(_rows), selection=None, show_column_summaries=False)
    return


@app.cell
def _(mo, snapshot):
    mo.md(f"""
    ## Notes and caveats

    - **Projected strength, not standings.** Team values come from each player's last games in
      the window, which early in the season is mostly last season. "Rank" here is a team's place
      by projected per-period value, not its record.
    - **Who makes room matters.** Flat SGP is linear, so the *Swap out* choice shifts every
      player equally and never reorders them. xWCWA is a curve: a different starting point lands
      candidates on different stretches of it, and the order can change a lot. The weakest-player
      swap is closer to a real waiver move.
    - **Supply is shown, not scored.** Section 3's waiver-wire scarcity isn't part of xWCWA. xWCWA
      weights by the competition only.
    - **Short windows.** With shrinkage on, a one- or two-game player is pulled most of the way
      to the typical player. *Min games* still hides them from the leaderboard.
    - **Shrinkage is toward the whole pool**, not toward similar players, so a starter's
      steals shrink toward a typical (lower-minute) player's. A minutes- or position-based prior
      would be sharper. The weekly noise comes from the simulation's raw projections.
    - **Turnovers** count as a negative stat throughout: fewer is a rank gain.
    - **Ties and ends (season ranks).** Passing first place gains nothing more. Falling below last
      costs ranks at the category's median gap per rank.
    - **Small league, noisy gaps.** With {len(snapshot.teams)} teams, any single gap is one
      pair of teams. Read the shape against the null, not gap by gap.
    """)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
