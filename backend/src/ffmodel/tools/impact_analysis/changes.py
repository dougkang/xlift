"""Before/after comparison of an analysis (003 research R2, R3).

Every change is computed here: signed, rounded to the precision the page shows, and classified
better / worse / neutral from the selected team's point of view. The page only renders it.
"""

import math

# Display precision (research R2).
COUNT_DECIMALS = 0  # W/L/T, ranks
PCT_DECIMALS = 0  # win %, chance to win: whole percentage points (scale 100)
AREA_DECIMALS = 0  # 0-100 area score (scale 100)
COUNT_AVG_DECIMALS = 1
RATIO_AVG_DECIMALS = 3

RESULT_ORDER = {"loss": 0, "tie": 1, "win": 2}


def avg_decimals(category) -> int:
    return RATIO_AVG_DECIMALS if category.kind == "ratio" else COUNT_AVG_DECIMALS


def tone(delta: float, better_when: str) -> str:
    """'better' / 'worse' / 'neutral' for a non-zero delta (better_when: higher/lower/neutral)."""
    if better_when == "neutral" or delta == 0:
        return "neutral"
    up = delta > 0
    return "better" if up == (better_when == "higher") else "worse"


def change(current, original, *, decimals: int, better_when: str, scale: float = 1.0):
    """A Change {delta, tone}, or None if missing on either side or zero at display precision."""
    if current is None or original is None:
        return None
    try:
        cur, orig = float(current), float(original)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(cur) and math.isfinite(orig)):
        return None
    delta = round((cur - orig) * scale, decimals)
    if delta == 0:
        return None
    return {"delta": delta, "tone": tone(delta, better_when)}


def transition(original: str, current: str) -> str | None:
    """Result transition, ordered L < T < W; only L<->W counts as a flip."""
    a, b = RESULT_ORDER[original], RESULT_ORDER[current]
    if a == b:
        return None
    if (original, current) == ("loss", "win"):
        return "flip_better"
    if (original, current) == ("win", "loss"):
        return "flip_worse"
    return "better" if b > a else "worse"


# --- The `changes` block (003 contracts/api.md) ----------------------------------------------


def _dir(cat: dict) -> str:
    return "higher" if cat["higher_is_better"] else "lower"


def _inverse(cat: dict) -> str:
    return "lower" if cat["higher_is_better"] else "higher"


def _avg_dec(cat: dict) -> int:
    # Ratio categories are the ones the format displays with decimals (FG%, FT%).
    return RATIO_AVG_DECIMALS if cat["decimals"] > 0 else COUNT_AVG_DECIMALS


def _wlt(cur: dict, orig: dict) -> dict:
    return {
        "wins": change(cur["wins"], orig["wins"], decimals=COUNT_DECIMALS, better_when="higher"),
        "losses": change(
            cur["losses"], orig["losses"], decimals=COUNT_DECIMALS, better_when="lower"
        ),
        "ties": change(cur["ties"], orig["ties"], decimals=COUNT_DECIMALS, better_when="neutral"),
    }


def _pct(cur, orig) -> dict | None:
    return change(cur, orig, decimals=PCT_DECIMALS, better_when="higher", scale=100)


def _expected_wins(cur: dict, orig: dict) -> dict | None:
    """Change in category wins as the page shows them: the difference of the whole records
    (010 R4)."""
    return change(
        cur["record"]["wins"], orig["record"]["wins"], decimals=COUNT_DECIMALS, better_when="higher"
    )


_NO_WLT = {"wins": None, "losses": None, "ties": None}


RADAR_TONE_DECIMALS = 2  # a radar marker appears once a spoke moves by >= 1% of the radius


def _radar_tones(cur: dict, orig: dict) -> dict:
    def tones(field, better_when, decimals):
        out = []
        for c, o in zip(cur[field], orig[field], strict=True):
            ch = change(c, o, decimals=decimals, better_when=better_when)
            out.append(ch["tone"] if ch else None)
        return out

    return {
        "rank": tones("ranks", "lower", COUNT_DECIMALS),
        "average": tones("normalized", "higher", RADAR_TONE_DECIMALS),
        "win_rate": tones("win_rate", "higher", RADAR_TONE_DECIMALS),
    }


def build_changes(original: dict, current: dict, orig_comp, comp, s) -> dict:
    """Every before/after comparison the page shows, classified for the selected team."""
    cats = current["categories"]
    tactical = s.mode == "tactical"
    me, opp = s.team_id, s.opponent_id
    each = current["standings"] == "category"

    # 1-2. Headline. Each-category: the change in expected category wins, and in strategic the
    # standings win % (010 FR-015).
    if each:
        cur_exp, orig_exp = (
            current["header"]["expected_record"],
            original["header"]["expected_record"],
        )
        header = {
            **_NO_WLT,
            "chance_to_win": None,
            "expected_wins": _expected_wins(cur_exp, orig_exp),
            "win_pct": None if tactical else _pct(cur_exp["win_pct"], orig_exp["win_pct"]),
        }
    elif tactical:
        header = {
            "wins": None,
            "losses": None,
            "ties": None,
            "chance_to_win": _pct(
                current["header"]["matchup_win_probability"],
                original["header"]["matchup_win_probability"],
            ),
            "expected_wins": None,
            "win_pct": None,
        }
    else:
        header = {
            **_wlt(current["header"]["record"], original["header"]["record"]),
            "chance_to_win": None,
            "expected_wins": None,
            "win_pct": None,
        }

    # 3-4. Radar
    cur_series = {r["team_id"]: r for r in current["radar"]["series"]}
    orig_series = {r["team_id"]: r for r in original["radar"]["series"]}
    show = [me]
    if tactical and orig_comp.active.get(opp) != comp.active.get(opp):
        show.append(opp)
    radar = {
        "original": [
            {
                k: orig_series[t][k]
                for k in ("team_id", "emphasis", "ranks", "normalized", "win_rate")
            }
            for t in show
        ],
        "tones": {str(t): _radar_tones(cur_series[t], orig_series[t]) for t in show},
        "area": {
            scale: change(
                cur_series[me]["area"][scale],
                orig_series[me]["area"][scale],
                decimals=AREA_DECIMALS,
                better_when="higher",
                scale=100,
            )
            for scale in ("rank", "average", "win_rate")
        },
    }

    # 5-6. Category table
    table = {}
    orig_rows = {r["category"]: r for r in original["category_table"]["rows"]}
    for cat, row in zip(cats, current["category_table"]["rows"], strict=True):
        o, d = orig_rows[cat["key"]], _avg_dec(cat)
        if tactical:
            table[cat["key"]] = {
                "selected_average": change(
                    row["selected_average"],
                    o["selected_average"],
                    decimals=d,
                    better_when=_dir(cat),
                ),
                "opponent_average": change(
                    row["opponent_average"],
                    o["opponent_average"],
                    decimals=d,
                    better_when=_inverse(cat),
                ),
                "difference": change(
                    row["difference"], o["difference"], decimals=d, better_when=_dir(cat)
                ),
                "win_probability": _pct(row["win_probability"], o["win_probability"]),
            }
        else:
            table[cat["key"]] = {
                "rank": change(
                    row["rank"], o["rank"], decimals=COUNT_DECIMALS, better_when="lower"
                ),
                "average": change(row["average"], o["average"], decimals=d, better_when=_dir(cat)),
                "league_average": change(
                    row["league_average"], o["league_average"], decimals=d, better_when="neutral"
                ),
                "leader_average": change(
                    row["leader_average"], o["leader_average"], decimals=d, better_when="neutral"
                ),
                "win_rate": _pct(row["win_rate"], o["win_rate"]),
            }

    # 7. Curves: change of the plotted averages (originals are extra series in the curves).
    orig_curves = {c["category"]: c for c in original["curves"]}
    curves = {}
    for cat, curve in zip(cats, current["curves"], strict=True):
        before = {s_["role"]: s_["mean"] for s_ in orig_curves[cat["key"]]["series"]}
        means = {}
        for series in curve["series"]:
            role = series["role"]
            if role not in ("selected", "opponent"):
                continue
            means[role] = change(
                series["mean"],
                before.get(role),
                decimals=_avg_dec(cat),
                better_when=_dir(cat) if role == "selected" else _inverse(cat),
            )
        curves[cat["key"]] = {"means": means}

    # 8. H2H rows. Each-category has no matchup result, so no flips (010 FR-016).
    orig_matchups = {m["opponent_id"]: m for m in original["matchups"]}
    matchups = {}
    for m in current["matchups"]:
        o = orig_matchups[m["opponent_id"]]
        matchups[str(m["opponent_id"])] = {
            "category_record": _wlt(m["category_record"], o["category_record"]),
            "win": _pct(m["matchup"]["win"], o["matchup"]["win"]),
            "original_result": None if each else o["result"],
            "transition": None if each else transition(o["result"], m["result"]),
            "expected_wins": _expected_wins(m["expected_record"], o["expected_record"])
            if each
            else None,
        }

    # 9. H2H totals (none in tactical: the opponent's roster replaces H2H, 005)
    cur_t, orig_t = current["matchup_totals"], original["matchup_totals"]
    totals = None
    if cur_t and orig_t:
        totals = {
            "matchups": None if each else _wlt(cur_t["matchups"], orig_t["matchups"]),
            "categories": _wlt(cur_t["categories"], orig_t["categories"]),
            "expected_wins": _expected_wins(cur_t["expected"], orig_t["expected"])
            if each
            else None,
        }
    return {
        "header": header,
        "radar": radar,
        "category_table": table,
        "curves": curves,
        "matchups": matchups,
        "matchup_totals": totals,
    }
