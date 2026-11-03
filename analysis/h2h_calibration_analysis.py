import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full", app_title="H2H Calibration")


@app.cell
def _():
    from datetime import date

    import altair as alt
    import marimo as mo
    import numpy as np
    import polars as pl

    import h2h_calibration as hc
    from ffmodel.contract.db import get_engine

    # docs/style.md: primary (yours), secondary (others), tertiary (league references).
    PRIMARY, PRIMARY_LIGHT, SECONDARY, TERTIARY = "#1C324A", "#9DC0F5", "#CE7955", "#898240"
    return PRIMARY, PRIMARY_LIGHT, SECONDARY, TERTIARY, alt, date, get_engine, hc, mo, np, pl


@app.cell
def _(mo):
    mo.md(r"""
    # H2H Calibration

    In week 1 the strategic H2H's favorite won only 4 of 9 matchups, and two teams it gave
    97% and 77% lost badly (issue #6). This report measures **why**. Each week is tested with
    projections from the day before it starts, against the box scores of the league's current
    active rosters.

    - **Week 1** (Oct 20–25): projections as of Oct 19, before any game of the season.
    - **Week 2 so far** (Oct 26–30): projections as of Oct 25, with week 1's games in them.
    """)
    return


@app.cell
def _(date, get_engine, hc):
    conn = get_engine().connect()
    lg = hc.load(conn)
    W1 = hc.Window("week 1", date(2026, 10, 19), date(2026, 10, 20), date(2026, 10, 25))
    W2 = hc.Window("week 2 so far", date(2026, 10, 25), date(2026, 10, 26), date(2026, 10, 30))
    # Week 1's pairings (the league only keeps the current week's matchups).
    WEEK1_PAIRS = [(1, 3), (2, 18), (4, 8), (5, 9), (6, 17), (7, 16), (10, 13), (11, 14), (12, 15)]
    return W1, W2, WEEK1_PAIRS, lg


@app.cell
def _(W1, W2, hc, lg, pl):
    avail = pl.concat([hc.availability(lg, W1), hc.availability(lg, W2)])
    games = pl.concat([hc.games(lg, W1), hc.games(lg, W2)])
    z = pl.concat([hc.per_game_z(lg, W1), hc.per_game_z(lg, W2)])
    return avail, games, z


@app.cell
def _(W1, WEEK1_PAIRS, hc, lg):
    cover = hc.coverage(lg, W1)
    rescored = hc.rescore(lg, W1, WEEK1_PAIRS)
    rebuild, rebuild_agree, rebuild_total, rebuild_window = hc.rebuild_check(lg)
    return cover, rebuild, rebuild_agree, rebuild_total, rebuild_window, rescored


@app.cell
def _(avail, cover, games, mo, np, pl, rebuild_agree, rebuild_total, rescored, z):
    def _stat(week, col):
        d = avail.filter(pl.col("week") == week)
        return d[col].mean(), d["played"].mean(), float(np.corrcoef(d[col], d["played"])[0, 1])

    _p1, _a1, _c1 = _stat("week 1", "dAB × tag")
    _p2, _a2, _c2 = _stat("week 2 so far", "dAB × tag")
    _g1 = games.filter(pl.col("week") == "week 1")
    _rookies = avail.filter((pl.col("week") == "week 1") & (pl.col("history") == 0))
    _zsd = z.group_by("stat").agg(pl.col("mean taken as exact").std())["mean taken as exact"]
    _inside = cover.filter(pl.col("variant") == "app (3 games × dAB)").with_columns(
        inside=(pl.col("position") > 0.1) & (pl.col("position") < 0.9)
    )["inside"].mean()
    _r = {r["model"]: r for r in rescored.iter_rows(named=True)}
    mo.md(f"""
    ## Summary

    Four things make the H2H overconfident, roughly in order of size:

    1. **Availability was badly underestimated before week 1.** dAB × tag predicted rostered
       starters would play **{_p1:.0%}** of their games; they played **{_a1:.0%}**, and the
       prediction barely tracked who did (correlation **{_c1:.2f}**). By week 2 it's better
       ({_p2:.0%} vs {_a2:.0%}, correlation {_c2:.2f}). The app expected
       **{_g1["app expects"].mean():.0f}** games per team in week 1; teams played
       **{_g1["actual"].mean():.0f}**.
    2. **Players without NBA history count as zero.** **{_rookies.height}** rostered rookies had no
       games before week 1, so they added nothing to their teams' projections; they played
       **{_rookies["played"].mean():.0%}** of their games.
    3. **The NBA schedule is ignored.** Strategic mode gives every player 3 games a week; NBA
       teams play 2–4. Using each team's schedule alone improves week 1's category Brier from
       **{_r["app as shipped"]["category Brier"]:.3f}** to
       **{_r["+ NBA schedule"]["category Brier"]:.3f}** (a coin flip is 0.250), and favorites from
       {_r["app as shipped"]["favorites won"]} to {_r["+ NBA schedule"]["favorites won"]}.
    4. **The weekly range is too narrow.** Given each player's actual games, his totals miss by
       **{_zsd.min():.2f}–{_zsd.max():.2f}×** the model's spread (1.0 is calibrated). Only
       **{_inside:.0%}** of week-1 team totals fell inside the app's 80% range.

    And one limit no player model fixes: rebuilding a week from today's active rosters picks the
    league's real category winner in only **{rebuild_agree} of {rebuild_total}** contests, because
    managers change daily lineups and stream players.
    """)
    return


@app.cell
def _(PRIMARY, SECONDARY, alt, avail, mo, pl):
    _binned = (
        avail.with_columns(bin=(pl.col("dAB × tag") * 5).floor().clip(0, 4) / 5 + 0.1)
        .group_by("week", "bin")
        .agg(predicted=pl.col("dAB × tag").mean(), played=pl.col("played").mean(), players=pl.len())
        .filter(pl.col("players") >= 5)  # a bin of one or two players is noise
        .sort("week", "bin")
    )
    _diag = alt.Chart(pl.DataFrame({"x": [0, 1], "y": [0, 1]})).mark_line(
        strokeDash=[2, 3], color="#888"
    ).encode(x="x:Q", y="y:Q")
    _lines = alt.Chart(_binned).mark_line(point=True).encode(
        x=alt.X("predicted:Q", title="Predicted availability (dAB × tag)", scale=alt.Scale(domain=[0, 1])),
        y=alt.Y("played:Q", title="Share of team games played", scale=alt.Scale(domain=[0, 1])),
        color=alt.Color("week:N", scale=alt.Scale(range=[SECONDARY, PRIMARY]), title=None),
        tooltip=["week", alt.Tooltip("predicted:Q", format=".2f"), alt.Tooltip("played:Q", format=".2f"), "players"],
    )
    _summary = (
        avail.group_by("week")
        .agg(
            [pl.col(c).mean().alias(f"{c} (mean)") for c in ("dAB", "dAB × tag", "Last 15")]
            + [pl.col("played").mean().alias("played (mean)")]
            + [pl.corr(c, "played").alias(f"{c} corr") for c in ("dAB", "dAB × tag", "Last 15")]
        )
        .sort("week")
        .with_columns(pl.selectors.float().round(2))
    )
    mo.vstack(
        [
            mo.md(r"""
    ## 1. Availability

    How often a player plays scales every counting stat. Before week 1, dAB came from the end of
    last season and earlier seasons, which include late-season rest, shutdowns and tanking, while
    the league's rostered starters are mostly healthy. Points below the dotted line mean players
    played more than predicted (bins of fewer than 5 players are left out). Every option (plain
    dAB, with the injury tag, last 15 games) was off by about the same before week 1.
    """),
            (_diag + _lines).properties(width=420, height=320),
            _summary,
        ]
    )
    return


@app.cell
def _(avail, mo, pl):
    _r = avail.filter((pl.col("week") == "week 1") & (pl.col("history") == 0))
    mo.vstack(
        [
            mo.md(r"""
    ## 2. Players without NBA history

    A rookie with no NBA games has no projection, so the simulation leaves him out entirely: his
    team plays a man short. These rostered starters had no history before week 1:
    """),
            _r.select("player", "status", (pl.col("played") * 100).round(0).cast(pl.Int64).alias("% of games played")).rename(
                {"status": "tag today"}
            ),
        ]
    )
    return


@app.cell
def _(PRIMARY, SECONDARY, alt, games, mo, np, pl, rescored):
    _g = games.filter(pl.col("week") == "week 1").unpivot(
        index=["team", "actual"], on=["app expects", "schedule × dAB"], variable_name="expected by", value_name="expected"
    )
    _corr = {
        k: float(np.corrcoef(d["expected"], d["actual"])[0, 1])
        for (k,), d in _g.group_by("expected by")
    }
    _chart = alt.Chart(_g).mark_circle(size=60, opacity=0.8).encode(
        x=alt.X("expected:Q", title="Games expected", scale=alt.Scale(zero=False)),
        y=alt.Y("actual:Q", title="Games played (active slots)", scale=alt.Scale(zero=False)),
        color=alt.Color("expected by:N", scale=alt.Scale(range=[SECONDARY, PRIMARY]), title=None),
        tooltip=["team", "expected by", alt.Tooltip("expected:Q", format=".1f"), "actual"],
    ).properties(width=420, height=300)
    mo.vstack(
        [
            mo.md(f"""
    ## 3. The NBA schedule

    Strategic mode gives every player 3 games a week (times his availability). But NBA teams play
    2 to 4 games a week, so some fantasy teams get several more games than others. Week 1, one
    dot per fantasy team: games expected from the app's 3 games
    (correlation with what happened **{_corr["app expects"]:.2f}**) versus from each NBA team's
    actual schedule (**{_corr["schedule × dAB"]:.2f}**).
    """),
            _chart,
            mo.md(r"""
    Week 1 re-scored under changes to the simulation, one added at a time. *Confident calls that
    held*: of the categories called at 80% or more (either way), how often the favorite won it.
    Lower Brier is better; a coin flip scores 0.250. (Against rebuilt totals, so see section 5.)
    """),
            rescored.with_columns(
                pl.col("category Brier", "matchup Brier").round(3), pl.col("confident calls that held").round(2)
            ),
        ]
    )
    return


@app.cell
def _(PRIMARY, PRIMARY_LIGHT, alt, cover, lg, mo, pl, z):
    _sd = (
        z.unpivot(index=["week", "stat"], on=["mean taken as exact", "with its uncertainty"], variable_name="model", value_name="z")
        .group_by("week", "stat", "model")
        .agg(sd=pl.col("z").std())
    )
    def _week(week):
        bars = alt.Chart(_sd.filter(pl.col("week") == week)).mark_bar().encode(
            x=alt.X("stat:N", title=None, sort=lg.stats),
            xOffset="model:N",
            y=alt.Y("sd:Q", title="Miss ÷ model spread (SD)", scale=alt.Scale(domain=[0, 1.4])),
            color=alt.Color("model:N", scale=alt.Scale(range=[PRIMARY, PRIMARY_LIGHT]), title=None),
            tooltip=["week", "stat", "model", alt.Tooltip("sd:Q", format=".2f")],
        )
        one = alt.Chart(pl.DataFrame({"y": [1.0]})).mark_rule(color="#111").encode(y="y:Q")
        return (bars + one).properties(width=520, height=220, title=week)
    _cov = (
        cover.with_columns(inside=(pl.col("position") > 0.1) & (pl.col("position") < 0.9))
        .group_by("variant", "category")
        .agg(pl.col("inside").mean())
        .pivot(on="category", index="variant", values="inside")
        .select("variant", *lg.categories)
        .with_columns(pl.col(lg.categories).round(2))
        .sort(pl.col("variant").replace_strict(
            {"app (3 games × dAB)": 0, "actual games": 1, "actual games + mean uncertainty": 2}, default=3
        ))
    )
    mo.vstack(
        [
            mo.md(r"""
    ## 4. The weekly range

    Even with the right number of games, the simulated spread is too narrow. For each player,
    his totals over the week, given the games he actually played, are compared with the model's
    per-game spread. A calibrated model gives bars at 1.0. They sit at 1.1–1.3 in both weeks.
    Adding the uncertainty in each player's average (the simulation treats it as exact) barely
    helps: real swings and role changes are wider than the past games suggest.
    """),
            alt.vconcat(_week("week 1"), _week("week 2 so far")),
            mo.md(r"""
    Team totals in week 1: the share that fell inside the simulated 80% range, per category
    (0.80 when calibrated).
    """),
            _cov,
        ]
    )
    return


@app.cell
def _(PRIMARY, alt, mo, rebuild, rebuild_agree, rebuild_total, rebuild_window):
    mo.vstack(
        [
            mo.md(f"""
    ## 5. What no player model fixes

    The league's real totals come from daily lineups and pickups, not from one fixed roster. The
    current week so far ({rebuild_window.start}–{rebuild_window.end}), rebuilt from today's active
    rosters and box scores, misses the league's own totals by this much per stat, and picks the
    same category winner in **{rebuild_agree} of {rebuild_total}** contests. Every test against
    league results, this one included, carries that noise.
    """),
            alt.Chart(rebuild).mark_bar(color=PRIMARY).encode(
                x=alt.X("stat:N", sort=None, title=None),
                y=alt.Y("error:Q", title="Mean error vs the league's totals", axis=alt.Axis(format="%")),
                tooltip=["stat", alt.Tooltip("error:Q", format=".0%")],
            ).properties(width=420, height=220),
        ]
    )
    return


@app.cell
def _(W1, hc, lg, mo):
    def _team(team):
        s, df = hc.team_breakdown(lg, W1, team)
        return mo.vstack(
            [
                mo.md(
                    f"**{lg.team_names[team]}**: expected {s['games expected']:.0f} games and"
                    f" {s['points expected']:.0f} points; played {s['games played']}, scored"
                    f" {s['points scored']:.0f}."
                ),
                df,
            ]
        )

    mo.vstack(
        [
            mo.md(r"""
    ## 6. The two worst misses

    **Elsie's World (97%) vs Woo-Tang 4eva**, lost 3–6: Woo-Tang's rookie had no projection, and
    two of its guards had availability near 45%; they all played every game.
    """),
            _team(18),
            _team(2),
            mo.md(r"""
    **🥭 smoothie's team (77%) vs God's Favorite Danny**, lost 1–7–1: Danny's healthy players
    were given 54–74% availability, and every one played every game.
    """),
            _team(14),
            _team(11),
        ]
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Caveats

    - **Small sample**: 9 matchups, 81 category contests in week 1.
    - **Today's rosters and tags**: moves made during a week count as made before it, and the
      injury tag is today's, so a player tagged Out now but healthy in week 1 is penalized here.
      Plain dAB, without tags, was off by nearly as much, so the conclusion stands.
    - **A strict test**: strategic H2H describes a typical week, and this scores it against
      particular weeks. A 97% favorite losing 3–6 is still a calibration problem.

    ## What would fix it

    1. **Early-season availability**: until about 10 current-season games exist, lean dAB toward
       a high prior for healthy rostered players, and weight the end of last season less.
    2. **Rookies**: give players without history a typical-player projection instead of none.
    3. **The schedule**: use each NBA team's games for an H2H against a specific week (tactical
       mode already does for the current week).
    4. **The spread**: widen per-game swings (about ×1.2), or model minutes and role uncertainty.
    """)
    return


if __name__ == "__main__":
    app.run()
