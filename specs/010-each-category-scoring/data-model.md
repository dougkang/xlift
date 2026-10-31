# Data Model: H2H Each-Category Scoring

No schema change. The league's existing `fantasy_league.scoring_format_id` selects the format,
and the format declares the standings rule.

## ScoringFormat (core, extended)

| Field | Type | Notes |
|---|---|---|
| `standings` | `"matchup"` \| `"category"` | Default `"matchup"`. How a matchup enters the standings. |

Registered formats:

| id | name | standings |
|---|---|---|
| `9cat_h2h` | 9-category head-to-head | matchup (unchanged) |
| `9cat_h2h_each` | 9-category head-to-head, each category | category |

The two share categories, base stats, derived stats, constraints and unshrunk stats.

## ExpectedRecord (core)

| Field | Type | Rule |
|---|---|---|
| `wins` | float | Σ over categories (and opponents) of P(win) |
| `losses` | float | Σ P(loss) |
| `ties` | float | Σ P(tie) |
| `win_pct` | float | (W + ½T) ÷ (W + L + T); 0 when the total is 0 |

Invariants: per opponent, W + L + T = number of categories; records add component-wise.

## Result additions (see contracts/api.md)

- `standings` on every result.
- `header.expected_record` (category rule), `header.record` null then.
- H2H row: `expected_record`; `result` null under the category rule.
- `matchup_totals.expected`; `matchup_totals.matchups` null under the category rule.
- Changes: `header.expected_wins`, `header.win_pct`, row `expected_wins`,
  totals `expected_wins`.
