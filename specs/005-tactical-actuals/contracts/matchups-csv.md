# Contract: `matchups.csv` import

Produced by `~/dev/ccsv-rumble-page/tools/chrome_capture.py matchups --week N`.

## Columns

| Column | Required | Meaning |
|---|---|---|
| `week` | yes | Fantasy week number; the same on every row |
| `team_id` | yes | Same identifier as `rosters.csv` (`t.01` …) |
| `opponent_id` | yes | The team's opponent this week; must be mutual |
| `fgm`, `fga` | yes | Field goals made and attempted, week to date |
| `ftm`, `fta` | yes | Free throws made and attempted |
| `tpm` | yes | 3-pointers made (stored as `fg3m`) |
| `pts` | yes | Points; must equal `2·fgm + tpm + ftm` (cross-check only) |
| `reb`, `ast`, `stl`, `blk` | yes | Counting stats |
| `to` | yes | Turnovers (stored as `tov`) |
| `matchup`, `team_name`, `fg_pct_display`, `ft_pct_display`, `cat_wins` | no | Ignored |

One row per team. Every team in the league must appear exactly once.

## Validation (all-or-nothing)

| Problem | Report label |
|---|---|
| A required column is missing | `MISSING` |
| A value isn't a non-negative integer | `MALFORMED` |
| An unknown team, or a team appearing twice | `UNKNOWN_TEAM` / `DUPLICATE` |
| A league team with no row | `MISSING_TEAM` |
| A team plays itself, or the pairing isn't mutual | `BAD_PAIRING` |
| The week differs between rows | `INCONSISTENT` |
| `fgm > fga`, `ftm > fta`, `tpm > fgm`, or `pts ≠ 2·fgm + tpm + ftm` | `BAD_TOTALS` |

## CLI

```bash
ffm load matchups PATH --league-key KEY [--as-of YYYY-MM-DD] [--period-start D --period-end D]
```

- **`--as-of`:** defaults to the file's last-modified date (local time). A file modified before
  noon counts as the previous day, so a capture just after midnight describes the evening before.
  `ffm load roster` uses the same rule.
- **Period:** defaults to the Monday–Sunday week containing the as-of date.
- **Output:** the summary prints the week, the period, the as-of date, the pairings (team names),
  and the inserted and replaced counts. `--json` is supported as for the other loaders.
- **Exit codes:** `0` on success, `2` when the file is rejected, `1` on errors.

`ffm load roster` changes only its `--as-of` default, from today to the file's last-modified
date.
