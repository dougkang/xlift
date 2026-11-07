"""Backtest of next-week and next-two-week player projections over 2025-26 (ccsv-rumble #33).

Every Monday, each model predicts each player's totals for the coming Mon-Sun week, the week
after it, and the two together, using only games before that Monday:

- **espn**: ESPN's per-game line × the club's games (what ccsv-rumble does today, assuming a
  player plays every game);
- **espn_out**: espn, with players who missed every club game of the past 7 days projected at
  zero (a stand-in for the league's IL slots, whose 2025-26 history isn't kept);
- **espn_avail**: espn × xlift's 15-game availability;
- **xlift**: the shipped ``build_projections`` line × club games × availability;
- **xlift_out**, **xlift_out_avail**: the xlift line with the zero rule, without and with
  availability;
- **std_out**, **std_avail**, **std**: the season-to-date average with the zero rule, with
  availability, and assuming every game;
- **last15**, **last_season**: the last 15 games and last season's average, assuming every game.

ESPN's line is one snapshot, and the served 2025-26 set looks preseason (see the write-up), so
espn doesn't update during the season. All models are scored on the same players: those ESPN
projects, ranked by the average of their espn and xlift value ranks, so no model chooses a pool
that flatters it. FG% and FT% are scored as impact, makes minus the league rate × attempts.

Needs the season before the one tested. Load 2024-25 into a copy of the database:

    cp data/ffmodel.sqlite /tmp/backtest.sqlite
    export FFMODEL_DB_URL=sqlite:////tmp/backtest.sqlite
    (cd backend && uv run ffm load nba --season 2024-25)
    (cd analysis && uv run python weekly_backtest.py)
"""

import json
import re
import unicodedata
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl
from ffmodel.contract.db import get_engine
from ffmodel.core.model import build_projections
from ffmodel.core.scoring import get_format

SEASON, PRIOR_SEASON = "2025-26", "2024-25"
ESPN_SEASON = 2026  # ESPN labels a season by its end year
FIRST_CUTOFF, LAST_CUTOFF = date(2025, 10, 27), date(2026, 4, 6)
SEASON_END = date(2026, 4, 12)
ALL_STAR_WEEK = (date(2026, 2, 16), date(2026, 2, 22))
EARLY_END, FINAL_START = date(2025, 11, 24), date(2026, 3, 16)  # weeks 2-6; the last four weeks
POOLS = (180, 250)
STAR_POINTS = 20
LINE = ("pts", "reb", "ast", "stl", "blk", "fg3m", "tov", "fgm", "fga", "ftm", "fta")
L = {s: i for i, s in enumerate(LINE)}
CATS = ("pts", "reb", "ast", "stl", "blk", "fg3m", "tov", "fg_impact", "ft_impact")
MODELS = (
    "espn", "espn_out", "espn_avail", "xlift", "xlift_out", "xlift_out_avail",
    "std_out", "std_avail", "std", "last15", "last_season",
)  # fmt: skip
HORIZONS = {"week+1": (0, 6), "week+2": (7, 13), "weeks+1-2": (0, 13)}

ESPN_URL = (
    "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/{season}"
    "/players?scoringPeriodId=0&view=kona_player_info"
)
ESPN_STAT = {
    "pts": "0", "blk": "1", "stl": "2", "ast": "3", "reb": "6", "tov": "11",
    "fgm": "13", "fga": "14", "ftm": "15", "fta": "16", "fg3m": "17",
}  # fmt: skip
ESPN_GP = "42"
ALIASES = {  # ESPN's spelling → nba_stats', where the two differ after normalizing
    "nicolas claxton": "nic claxton",
    "herbert jones": "herb jones",
    "cameron thomas": "cam thomas",
    "ronald holland": "ron holland",
    "alexandre sarr": "alex sarr",
    "carlton carrington": "bub carrington",
}
HERE = Path(__file__).parent
ESPN_CACHE = HERE / "output" / f"espn_{ESPN_SEASON}.json"


def norm_name(name: str) -> str:
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    plain = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", plain)
    plain = " ".join(re.sub(r"[^a-z ]", "", plain).split())
    return ALIASES.get(plain, plain)


def fetch_espn(cache: Path = ESPN_CACHE) -> list[dict]:
    """ESPN's player list for the season. The bare limit filter is deliberate: see
    ccsv-rumble's tools/espn_projections.js."""
    if not cache.exists():
        request = urllib.request.Request(
            ESPN_URL.format(season=ESPN_SEASON),
            headers={
                "X-Fantasy-Filter": json.dumps({"players": {"limit": 600}}),
                "User-Agent": "Mozilla/5.0",
            },
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read()
        cache.parent.mkdir(exist_ok=True)
        cache.write_bytes(body)
    return json.loads(cache.read_text())


def espn_lines(players: list[dict]) -> dict[str, np.ndarray]:
    """Per-game projected lines by normalized name."""
    out = {}
    for p in players:
        stats = next(
            (s for s in p.get("stats", []) if s["id"] == f"10{ESPN_SEASON}"),
            None,
        )
        games = (stats or {}).get("stats", {}).get(ESPN_GP)
        if games:
            out[norm_name(p["fullName"])] = np.array(
                [stats["stats"].get(ESPN_STAT[s], 0) / games for s in LINE]
            )
    return out


def cutoffs(first: date = FIRST_CUTOFF, last: date = LAST_CUTOFF) -> list[date]:
    return [first + timedelta(days=7 * k) for k in range((last - first).days // 7 + 1)]


def window(cutoff: date, horizon: str) -> tuple[date, date] | None:
    """The horizon's days, or None if it runs past the season or touches the All-Star break,
    whose short week the league's calendar treats differently."""
    start, end = (cutoff + timedelta(days=d) for d in HORIZONS[horizon])
    if end > SEASON_END or (start <= ALL_STAR_WEEK[1] and ALL_STAR_WEEK[0] <= end):
        return None
    return start, end


def missed_last_week(played: np.ndarray, club: np.ndarray, cutoff: str, week_ago: str) -> bool:
    """Did the player miss every game (at least two) their club played in the past 7 days?"""
    games = club[(club >= week_ago) & (club < cutoff)]
    return len(games) >= 2 and not np.isin(games, played).any()


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan")
    rx, ry = (pl.Series(v).rank("average").to_numpy() for v in (x, y))
    return float(np.corrcoef(rx, ry)[0, 1])


def categories(lines: np.ndarray, fg_rate: float, ft_rate: float) -> np.ndarray:
    """Lines → the league's nine categories, the two percentages as impact."""
    counting = lines[..., [L[c] for c in CATS[:7]]]
    fg = lines[..., L["fgm"]] - fg_rate * lines[..., L["fga"]]
    ft = lines[..., L["ftm"]] - ft_rate * lines[..., L["fta"]]
    return np.concatenate([counting, fg[..., None], ft[..., None]], axis=-1)


def value(cats: np.ndarray, sd: np.ndarray) -> np.ndarray:
    """One number across the categories, each in units of its spread. Turnovers count against."""
    signs = np.array([-1.0 if c == "tov" else 1.0 for c in CATS])
    return (cats / np.where(sd > 0, sd, 1.0) * signs).sum(axis=-1)


def value_rank(lines: np.ndarray, fg_rate: float, ft_rate: float) -> np.ndarray:
    """Rank of each per-game line, 0 for the most valuable."""
    cats = categories(lines, fg_rate, ft_rate)
    return pl.Series(-value(cats, cats.std(axis=0))).rank("average").to_numpy() - 1


def score(cutoff, horizon, pool, segment, model, pred, act, games_pred, games_act, rate, rate_act):
    """Metric rows for one model on one week's players. `pred`/`act` are (n, 9) category totals;
    `rate`/`rate_act` the same per game, for players who played."""
    sd = act.std(axis=0)
    rows = []
    for j, c in enumerate(CATS):
        err = pred[:, j] - act[:, j]
        rows.append(
            {
                "cat": c,
                "mae": np.abs(err).mean(),
                "nmae": np.abs(err).mean() / sd[j] if sd[j] else np.nan,
                "bias": err.mean(),
                "rank": spearman(pred[:, j], act[:, j]),
                "rate_mae": np.abs(rate[:, j] - rate_act[:, j]).mean() if len(rate) else np.nan,
                "rate_rank": spearman(rate[:, j], rate_act[:, j]),
            }
        )
    rows.append(
        {
            "cat": "value",
            "mae": np.abs(value(pred, sd) - value(act, sd)).mean(),
            "nmae": np.nan,
            "bias": (value(pred, sd) - value(act, sd)).mean(),
            "rank": spearman(value(pred, sd), value(act, sd)),
            "rate_mae": np.nan,
            "rate_rank": np.nan,
        }
    )
    rows.append(
        {
            "cat": "games",
            "mae": np.abs(games_pred - games_act).mean(),
            "nmae": np.nan,
            "bias": (games_pred - games_act).mean(),
            "rank": spearman(games_pred, games_act),
            "rate_mae": np.nan,
            "rate_rank": np.nan,
        }
    )
    key = {
        "cutoff": cutoff.isoformat(), "horizon": horizon, "pool": pool, "segment": segment,
        "model": model, "n": len(act),
    }  # fmt: skip
    return [{**key, **r} for r in rows]


@dataclass
class Logs:
    dates: dict[int, np.ndarray]
    lines: dict[int, np.ndarray]
    teams: dict[int, np.ndarray]
    names: dict[int, str]
    club_dates: dict[int, np.ndarray]
    prior_rows: dict[int, np.ndarray]  # 2024-25 per-game average
    league_rows: np.ndarray  # season's game lines, date-sorted, for league rates
    league_dates: np.ndarray


def load_logs(conn) -> Logs:
    cols = ", ".join(f"pg.{s}" for s in LINE)
    rows = conn.exec_driver_sql(
        f"""SELECT pg.player_id, g.game_date, g.season_id, pg.team_id, {cols}
            FROM player_game pg JOIN game g USING (game_id)
            WHERE g.season_type = 'regular' AND g.status = 'final' AND g.season_id IN (?, ?)
            ORDER BY pg.player_id, g.game_date""",
        (PRIOR_SEASON, SEASON),
    ).all()
    by = defaultdict(list)
    for r in rows:
        by[r[0]].append(r)
    dates, lines, teams, prior = {}, {}, {}, {}
    for pid, rs in by.items():
        old = [r for r in rs if r[2] == PRIOR_SEASON]
        dates[pid] = np.array([r[1] for r in rs])
        lines[pid] = np.array([r[4:] for r in rs], float)
        teams[pid] = np.array([r[3] for r in rs])
        if old:
            prior[pid] = np.array([r[4:] for r in old], float).mean(axis=0)
    club = defaultdict(set)
    games = conn.exec_driver_sql(
        """SELECT game_date, home_team_id, away_team_id FROM game
           WHERE season_type = 'regular' AND status = 'final' AND season_id = ?""",
        (SEASON,),
    ).all()
    for d, home, away in games:
        club[home].add(d)
        club[away].add(d)
    names = dict(conn.exec_driver_sql("SELECT player_id, full_name FROM player").all())
    season = [(r[1], r[4:]) for r in rows if r[2] == SEASON]
    season.sort(key=lambda r: r[0])
    return Logs(
        dates, lines, teams, names,
        {t: np.array(sorted(ds)) for t, ds in club.items()},
        prior,
        np.array([r[1] for r in season], float),
        np.array([r[0] for r in season]),
    )  # fmt: skip


def club_on(logs: Logs, pid: int, cut: str) -> int | None:
    """The club of the player's last game before the cutoff, else of the first after it."""
    d, t = logs.dates[pid], logs.teams[pid]
    k = int(np.searchsorted(d, cut))
    if k:
        return int(t[k - 1])
    return int(t[0]) if len(t) else None


def run(conn, logs: Logs, espn: dict[str, np.ndarray], fmt) -> tuple[list[dict], list[dict]]:
    """Metric rows, plus how much of each week's real value ESPN's set misses."""
    espn_by_id = {}
    unmatched = []
    pid_of = {norm_name(n): p for p, n in logs.names.items() if p in logs.dates}
    for name, line in espn.items():
        if name in pid_of:
            espn_by_id[pid_of[name]] = line
        else:
            unmatched.append(name)
    print(f"ESPN lines {len(espn)}: matched {len(espn_by_id)}; unmatched: {sorted(unmatched)}")
    ids = sorted(espn_by_id)
    base = list(fmt.base_stats)
    base_idx = {s: i for i, s in enumerate(base)}

    def from_base(mean: np.ndarray) -> np.ndarray:
        made = {s: mean[base_idx[s]] for s in ("fgm", "fg3m", "ftm")}
        pts = 2 * made["fgm"] + made["fg3m"] + made["ftm"]
        return np.array([pts if s == "pts" else mean[base_idx[s]] for s in LINE])

    metrics, coverage = [], []
    for cutoff in cutoffs():
        cut = cutoff.isoformat()
        week_ago = (cutoff - timedelta(days=7)).isoformat()
        day = cutoff - timedelta(days=1)
        shipped = build_projections(conn, ids, fmt, window=82, as_of=day)
        k = int(np.searchsorted(logs.league_dates, cut))
        fg_rate = logs.league_rows[:k, L["fgm"]].sum() / logs.league_rows[:k, L["fga"]].sum()
        ft_rate = logs.league_rows[:k, L["ftm"]].sum() / logs.league_rows[:k, L["fta"]].sum()

        kept, preds, avail, out = [], {m: [] for m in MODELS}, [], []
        season_start = logs.league_dates[0]
        for pid in ids:
            d, ls = logs.dates[pid], logs.lines[pid]
            k = int(np.searchsorted(d, cut))
            k0 = int(np.searchsorted(d, season_start))
            season_games = ls[k0:k]
            prior = logs.prior_rows.get(pid)
            std = season_games.mean(axis=0) if len(season_games) else prior
            last15 = ls[max(0, k - 15) : k].mean(axis=0) if k else None
            if std is None or last15 is None:
                continue  # hasn't played yet, and no last season: no simple average to compare
            team = club_on(logs, pid, cut)
            if team is None or team not in logs.club_dates:
                continue
            kept.append((pid, team))
            a = shipped[pid].availability
            avail.append(1.0 if a is None else a)
            played = d[k0:k]
            out.append(missed_last_week(played, logs.club_dates[team], cut, week_ago))
            preds["espn"].append(espn_by_id[pid])
            preds["xlift"].append(from_base(shipped[pid].mean))
            preds["std"].append(std)
            preds["last15"].append(last15)
            preds["last_season"].append(prior if prior is not None else std)
        pids = [p for p, _ in kept]
        lines = {m: np.array(v) for m, v in preds.items() if v}
        lines["espn_out"] = lines["espn_avail"] = lines["espn"]
        lines["xlift_out"] = lines["xlift_out_avail"] = lines["xlift"]
        lines["std_out"] = lines["std_avail"] = lines["std"]
        avail = np.array(avail)
        out = np.array(out)
        here = (~out).astype(float)
        volume = {
            "espn_out": here,
            "espn_avail": avail,
            "xlift": avail,
            "xlift_out": here,
            "xlift_out_avail": here * avail,
            "std_out": here,
            "std_avail": avail,
        }

        order = np.argsort(
            value_rank(lines["espn"], fg_rate, ft_rate)
            + value_rank(lines["xlift"], fg_rate, ft_rate)
        )
        pts = (lines["espn"][:, L["pts"]] + lines["xlift"][:, L["pts"]]) / 2

        for horizon in HORIZONS:
            span = window(cutoff, horizon)
            if span is None:
                continue
            lo, hi = span[0].isoformat(), span[1].isoformat()
            actual = np.zeros((len(pids), len(LINE)))
            games_act = np.zeros(len(pids))
            for i, pid in enumerate(pids):
                d = logs.dates[pid]
                mask = (d >= lo) & (d <= hi)
                actual[i] = logs.lines[pid][mask].sum(axis=0)
                games_act[i] = mask.sum()
            club_games = np.array(
                [((logs.club_dates[t] >= lo) & (logs.club_dates[t] <= hi)).sum() for _, t in kept],
                float,
            )
            act_cats = categories(actual, fg_rate, ft_rate)
            played = games_act > 0
            per_game = np.zeros_like(act_cats)
            per_game[played] = act_cats[played] / games_act[played][:, None]
            for pool in POOLS:
                top = order[:pool]
                segments = {
                    "all": np.ones(len(top), bool),
                    "stars": pts[top] >= STAR_POINTS,
                    "rest": pts[top] < STAR_POINTS,
                }
                for model in MODELS:
                    games_pred = club_games * volume.get(model, 1.0)
                    pred_lines = lines[model] * games_pred[:, None]
                    pred_cats = categories(pred_lines, fg_rate, ft_rate)
                    rate = categories(lines[model], fg_rate, ft_rate)
                    for segment, seg in segments.items():
                        if seg.sum() < 3:
                            continue
                        idx = top[seg]
                        idx_played = idx[played[idx]]
                        metrics += score(
                            cutoff, horizon, pool, segment, model,
                            pred_cats[idx], act_cats[idx], games_pred[idx], games_act[idx],
                            rate[idx_played], per_game[idx_played],
                        )  # fmt: skip

            if horizon == "week+1":
                coverage.append(week_coverage(logs, espn_by_id, cutoff, lo, hi, fg_rate, ft_rate))
        print(f"{cut}: {len(pids)} players scored of {len(ids)} projected", flush=True)
    return metrics, coverage


def week_coverage(logs, espn_by_id, cutoff, lo, hi, fg_rate, ft_rate) -> dict:
    """Of the week's real top 180, how many have no ESPN line?"""
    pids, totals = [], []
    for pid, d in logs.dates.items():
        mask = (d >= lo) & (d <= hi)
        if mask.any():
            pids.append(pid)
            totals.append(logs.lines[pid][mask].sum(axis=0))
    cats = categories(np.array(totals), fg_rate, ft_rate)
    top = np.argsort(-value(cats, cats.std(axis=0)))[:180]
    missing = [pids[i] for i in top if pids[i] not in espn_by_id]
    return {
        "cutoff": cutoff.isoformat(),
        "missing": len(missing),
        "of": len(top),
        "names": ", ".join(logs.names[p] for p in missing),
    }


def summarize(metrics: pl.DataFrame) -> str:
    """The write-up's tables: means over the weeks."""

    def table(frame: pl.DataFrame) -> str:
        head = "| " + " | ".join(frame.columns) + " |"
        rule = "|" + "---|" * len(frame.columns)
        body = [
            "| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in row) + " |"
            for row in frame.rows()
        ]
        return "\n".join([head, rule, *body])

    def by_model(frame: pl.DataFrame) -> pl.DataFrame:
        cats = frame.filter(pl.col("cat").is_in(CATS)).group_by("model").agg(
            pl.col("rank").mean().alias("cat_rank"), pl.col("nmae").mean().alias("nmae"),
            pl.col("rate_rank").mean().alias("rate_rank"),
        )  # fmt: skip
        val = frame.filter(pl.col("cat") == "value").group_by("model").agg(
            pl.col("rank").mean().alias("value_rank")
        )  # fmt: skip
        games = frame.filter(pl.col("cat") == "games").group_by("model").agg(
            pl.col("mae").mean().alias("games_mae"), pl.col("bias").mean().alias("games_bias"),
        )  # fmt: skip
        joined = val.join(cats, on="model").join(games, on="model")
        order = pl.DataFrame({"model": MODELS}).with_row_index("o")
        return joined.join(order, on="model").sort("o").drop("o")

    out = []
    everyone = metrics.filter(pl.col("segment") == "all")
    for horizon in HORIZONS:
        for pool in POOLS:
            part = everyone.filter((pl.col("horizon") == horizon) & (pl.col("pool") == pool))
            weeks = part["cutoff"].n_unique()
            out += [f"\n### {horizon}, top {pool} ({weeks} weeks)\n", table(by_model(part))]

    w1 = everyone.filter((pl.col("horizon") == "week+1") & (pl.col("pool") == 180))
    out.append("\n### Weeks a model beats a reference on value rank (week+1, top 180)\n")
    val = w1.filter(pl.col("cat") == "value").pivot(on="model", index="cutoff", values="rank")
    wins = [
        {
            "model": m,
            "beats_espn": int((val[m] > val["espn"]).sum()),
            "beats_espn_out": int((val[m] > val["espn_out"]).sum()),
            "of": len(val),
        }
        for m in MODELS[1:]
    ]
    out.append(table(pl.DataFrame(wins)))

    for metric, label in (("rank", "rank correlation"), ("mae", "total MAE"), ("bias", "total bias"),
                          ("rate_mae", "per-game MAE, when playing")):  # fmt: skip
        out.append(f"\n### By category: {label} (week+1, top 180)\n")
        in_cats = w1.filter(pl.col("cat").is_in(CATS))
        cats = in_cats.group_by("model", "cat").agg(pl.col(metric).mean())
        wide = cats.pivot(on="cat", index="model", values=metric).select("model", *CATS)
        order = pl.DataFrame({"model": MODELS}).with_row_index("o")
        out.append(table(wide.join(order, on="model").sort("o").drop("o")))

    out.append("\n### By period (week+1, top 180)\n")
    periods = w1.with_columns(
        pl.when(pl.col("cutoff") <= EARLY_END.isoformat()).then(pl.lit("early (weeks 2-6)"))
        .when(pl.col("cutoff") >= FINAL_START.isoformat()).then(pl.lit("final four weeks"))
        .otherwise(pl.lit("middle")).alias("period")
    )  # fmt: skip
    for period in ("early (weeks 2-6)", "middle", "final four weeks"):
        part = periods.filter(pl.col("period") == period)
        out += [f"\n{period}\n", table(by_model(part))]
        pts = part.filter(pl.col("cat") == "pts").group_by("model").agg(
            pl.col("rate_mae").mean().alias("pts_rate_mae")
        )  # fmt: skip
        order = pl.DataFrame({"model": MODELS}).with_row_index("o")
        out += ["\nPoints per game, when playing\n",
                table(pts.join(order, on="model").sort("o").drop("o"))]  # fmt: skip

    out.append("\n### Stars (averaged projection of 20+ points) vs the rest (week+1, top 180)\n")
    seg = metrics.filter((pl.col("horizon") == "week+1") & (pl.col("pool") == 180))
    for segment in ("stars", "rest"):
        out += [f"\n{segment}\n", table(by_model(seg.filter(pl.col("segment") == segment)))]
    stars_pts = seg.filter((pl.col("segment") == "stars") & (pl.col("cat") == "pts"))
    bias = stars_pts.group_by("model").agg(
        pl.col("bias").mean().alias("pts_total_bias"),
        pl.col("rate_mae").mean().alias("pts_rate_mae"),
    )
    order = pl.DataFrame({"model": MODELS}).with_row_index("o")
    out += ["\nStars' points\n", table(bias.join(order, on="model").sort("o").drop("o"))]
    return "\n".join(out)


def main():
    engine = get_engine()
    fmt = get_format("9cat_h2h")
    espn = espn_lines(fetch_espn())
    with engine.connect() as conn:
        loaded = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM game WHERE season_id = ?", (PRIOR_SEASON,)
        ).scalar_one()
        if not loaded:
            raise SystemExit(f"{PRIOR_SEASON} isn't loaded: see this file's docstring")
        logs = load_logs(conn)
        metrics, coverage = run(conn, logs, espn, fmt)
    out = HERE / "output"
    out.mkdir(exist_ok=True)
    frame = pl.DataFrame(metrics)
    frame.write_csv(out / "weekly_backtest.csv")
    cover = pl.DataFrame(coverage)
    cover.write_csv(out / "weekly_backtest_coverage.csv")
    summary = summarize(frame)
    summary += (
        f"\n\n### ESPN coverage\n\nOf each week's real top 180, on average "
        f"{cover['missing'].mean():.1f} have no ESPN line.\n"
    )
    (out / "weekly_backtest_summary.md").write_text(summary)
    print(summary)


if __name__ == "__main__":
    main()
