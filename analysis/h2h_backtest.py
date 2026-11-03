"""Backtest of the strategic H2H win rate against a completed week's matchups.

Run from analysis/:  uv run python h2h_backtest.py [--league 1] [--as-of 2026-10-19]

For each team, runs the shipped strategic analysis (``analyze``) and reads its H2H row for the
opponent it actually faced, then scores it against the league's loaded matchup totals:

- matchup level: favorite's record, Brier score and log loss (coin flip: .250 / .693), and the
  mean miss in categories won;
- category level: calibration (predicted chance to win a category vs how often it was won)
  and Brier score per category.

``--as-of`` defaults to the day before the matchup period starts, so no game from the week
leaks into the projections. Load the final matchup state first (scripts/daily_update.sh).
Rosters are the current ones: moves made during the week are treated as made before it.
"""

import argparse
import math
from datetime import date, timedelta

from sqlalchemy import text

from ffmodel.contract.db import get_engine
from ffmodel.core.data import get_matchup_state
from ffmodel.tools.impact_analysis.analysis import analyze
from ffmodel.tools.impact_analysis.settings import AnalysisSettings

CATEGORIES = ("fg_pct", "ft_pct", "fg3m", "pts", "reb", "ast", "stl", "blk", "tov")


def value(line: dict, cat: str) -> float:
    """A team's week total in a category, signed so higher always wins."""
    if cat == "fg_pct":
        return line["fgm"] / line["fga"] if line["fga"] else 0.0
    if cat == "ft_pct":
        return line["ftm"] / line["fta"] if line["fta"] else 0.0
    return -line["tov"] if cat == "tov" else line[cat]


def outcome(x: float, y: float) -> float:
    return 1.0 if x > y else 0.5 if x == y else 0.0


def record(a: dict, b: dict) -> tuple[int, int, int]:
    res = [outcome(value(a, c), value(b, c)) for c in CATEGORIES]
    return res.count(1.0), res.count(0.0), res.count(0.5)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--league", type=int, default=1)
    ap.add_argument("--as-of", type=date.fromisoformat, default=None)
    args = ap.parse_args()

    with get_engine().connect() as conn:
        state = get_matchup_state(conn, args.league)
        if state is None:
            raise SystemExit("no matchup state loaded for this league")
        as_of = args.as_of or state.period_start - timedelta(days=1)
        rows = conn.execute(
            text("SELECT * FROM matchup_team WHERE league_id = :l"), {"l": args.league}
        ).mappings()
        actual = {r["fantasy_team_id"]: dict(r) for r in rows}
        names = dict(conn.execute(text("SELECT fantasy_team_id, name FROM fantasy_team")).all())

        preds = {}
        for tid, line in actual.items():
            res = analyze(conn, AnalysisSettings(league_id=args.league, team_id=tid, as_of=as_of))
            opp = line["opponent_team_id"]
            preds[tid] = next(m for m in res["matchups"] if m["opponent_id"] == opp)

    final = "final" if state.as_of >= state.period_end else f"as of {state.as_of}, not final"
    print(f"Week {state.week} ({state.period_start} – {state.period_end}, {final})")
    print(f"Projections as of {as_of}\n")

    brier = logloss = favorites = cat_miss = 0.0
    shown = set()
    for tid, m in sorted(preds.items()):
        opp = actual[tid]["opponent_team_id"]
        w, lost, t = record(actual[tid], actual[opp])
        won = outcome(w, lost)
        p = m["matchup"]["win"]
        brier += (p - won) ** 2
        logloss -= math.log(max(1e-9, p if won == 1 else 1 - p if won == 0 else 0.5))
        favorites += (p > 0.5) == (won == 1)
        cat_miss += abs(m["category_record"]["wins"] - w)
        if tid in shown:
            continue
        shown |= {tid, opp}
        rec = m["category_record"]
        print(
            f"  {names[tid][:24]:24} vs {names[opp][:24]:24} win {p:4.0%}"
            f"  proj {rec['wins']}-{rec['losses']}-{rec['ties']}  actual {w}-{lost}-{t}"
            f"  {'✓' if (p > 0.5) == (won == 1) else '✗'}"
        )
    n = len(preds)
    print(
        f"\nFavorite won {favorites / 2:.0f} of {n // 2}   Brier {brier / n:.3f} (coin .250)"
        f"   log loss {logloss / n:.3f} (coin .693)   mean category miss {cat_miss / n:.2f}"
    )

    bins: dict[int, list[tuple[float, float]]] = {}
    by_cat: dict[str, list[float]] = {}
    for tid, m in preds.items():
        opp = actual[tid]["opponent_team_id"]
        for cat, pr in m["categories"].items():
            pw = pr["win"] + pr["tie"] / 2
            won = outcome(value(actual[tid], cat), value(actual[opp], cat))
            bins.setdefault(min(int(pw * 5), 4), []).append((pw, won))
            by_cat.setdefault(cat, []).append((pw - won) ** 2)
    print("\nCategory calibration (predicted chance → how often won):")
    for b, v in sorted(bins.items()):
        pred = sum(x for x, _ in v) / len(v)
        hit = sum(y for _, y in v) / len(v)
        print(f"  {b * 20:3d}–{b * 20 + 20}%: predicted {pred:.2f}  won {hit:.2f}  (n={len(v)})")
    print("Brier by category:")
    for cat in CATEGORIES:
        v = by_cat.get(cat, [])
        if v:
            print(f"  {cat:7} {sum(v) / len(v):.3f}")


if __name__ == "__main__":
    main()
