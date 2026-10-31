# Data Model: Trade Finder

No schema change.

**TradesRequest**: league_id, team_id, window (1–82), as_of, fragility.

**TradeRow**: team_id, team_name, manager, trade | null.

**Trade**: give (player_id, name, nba_team, status), get (same), your_gain (float), their_gain
(float), your_categories ([{category, gain}], |gain| ≥ 0.1, largest |gain| first).

**TradesResult**: settings echo, team_id, team_name, categories, rows (FR-007 order), warnings.
