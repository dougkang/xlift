# Contract: `matchups.csv` import

Produced by `~/dev/ccsv-rumble-page/tools/chrome_capture.py matchups`, one snapshot per day in
`data/matchups/YYYY-MM-DD.csv` (older captures wrote a single `data/matchups.csv`).

## Columns

| Column | Required | Meaning |
|---|---|---|
| `week` | yes | Fantasy week number. Only the latest week's rows are loaded: the snapshot taken the day a week ends also holds the previous week's final score |
| `team_id` | yes | Same identifier as `rosters.csv` (`t.01` …) |
| `opponent_id` | yes | The team's opponent this week; must be mutual |
| `fgm`, `fga` | yes | Field goals made and attempted, week to date |
| `ftm`, `fta` | yes | Free throws made and attempted |
| `tpm` | yes | 3-pointers made (stored as `fg3m`) |
| `pts` | yes | Points; must equal `2·fgm + tpm + ftm` (cross-check only) |
| `reb`, `ast`, `stl`, `blk` | yes | Counting stats |
| `to` | yes | Turnovers (stored as `tov`) |
| `week_start` | no | The week's first day (YYYY-MM-DD); the default period start when present |
| `week_end` | no | The week's last day as the scoreboard shows it; checked for agreement, not used (weeks end on Sunday) |
| `matchup`, `team_name`, `fg_pct_display`, `ft_pct_display`, `cat_wins`, `captured_at` | no | Ignored |

One row per team in the loaded week. Every team in the league must appear exactly once.

## Validation (all-or-nothing)

| Problem | Report label |
|---|---|
| A required column is missing | `MISSING` |
| A value isn't a non-negative integer | `MALFORMED` |
| An unknown team, or a team appearing twice | `UNKNOWN_TEAM` / `DUPLICATE` |
| A league team with no row | `MISSING_TEAM` |
| A team plays itself, or the pairing isn't mutual | `BAD_PAIRING` |
| `week_start`/`week_end` differ between the loaded rows | `INCONSISTENT` |
| `week_start` or `week_end` isn't a date | `MALFORMED` |
| `fgm > fga`, `ftm > fta`, `tpm > fgm`, or `pts ≠ 2·fgm + tpm + ftm` | `BAD_TOTALS` |

## CLI

```bash
ffm load matchups PATH --league-key KEY [--as-of YYYY-MM-DD] [--period-start D --period-end D]
```

- **`--as-of`:** defaults to the file's last-modified date (local time). A file modified before
  noon counts as the previous day, so a capture just after midnight describes the evening before.
  `ffm load roster` uses the same rule.
- **Period:** defaults to the file's `week_start` through that week's Sunday, else the
  Monday–Sunday week containing the as-of date. Weeks always end on Sunday but needn't start
  on Monday (week 1 of 2026-27 ran Tue Oct 20 – Sun Oct 25). The capture's `week_end` is
  ignored: it has shown a Monday (week 2 as Oct 26 – Nov 2).
- **Output:** the summary prints the week, the period, the as-of date, the pairings (team names),
  and the inserted and replaced counts. `--json` is supported as for the other loaders.
- **Exit codes:** `0` on success, `2` when the file is rejected, `1` on errors.

`ffm load roster` changes only its `--as-of` default, from today to the file's last-modified
date.
