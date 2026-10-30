"""9-category head-to-head: the first scoring format (contracts/scoring-format.md).

Two registrations share the categories and differ only in the standings rule (010 R1).
"""

from dataclasses import replace

from ffmodel.core.scoring.base import Category, ScoringFormat, register

NINE_CAT_H2H = register(
    ScoringFormat(
        id="9cat_h2h",
        name="9-category head-to-head",
        categories=(
            Category("pts", "PTS", "additive", stat="pts"),
            Category("reb", "REB", "additive", stat="reb"),
            Category("ast", "AST", "additive", stat="ast"),
            Category("stl", "STL", "additive", stat="stl"),
            Category("blk", "BLK", "additive", stat="blk"),
            Category("fg3m", "3PM", "additive", stat="fg3m"),
            Category("fg_pct", "FG%", "ratio", numerator="fgm", denominator="fga", decimals=3),
            Category("ft_pct", "FT%", "ratio", numerator="ftm", denominator="fta", decimals=3),
            Category("tov", "TO", "additive", stat="tov", higher_is_better=False),
        ),
        base_stats=("fgm", "fga", "fg3m", "ftm", "fta", "reb", "ast", "stl", "blk", "tov"),
        derived_stats={"pts": lambda t: 2 * t["fgm"] + t["fg3m"] + t["ftm"]},
        subset_constraints=(("fgm", "fga"), ("fg3m", "fgm"), ("ftm", "fta")),
        unshrunk_stats=("blk",),
    )
)

NINE_CAT_H2H_EACH = register(
    replace(
        NINE_CAT_H2H,
        id="9cat_h2h_each",
        name="9-category head-to-head, each category",
        standings="category",
    )
)
