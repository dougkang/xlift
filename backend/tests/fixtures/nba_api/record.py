"""Record trimmed nba_api responses for offline adapter tests (tasks.md T017).

Manual, needs network:  cd backend && uv run python -m tests.fixtures.nba_api.record
Responses are stored as the record lists NbaStatsClient returns, so the fake client can
serve them unchanged.
"""

import json
import math
from pathlib import Path

from nba_api.stats.endpoints import leaguegamelog, playerindex, scheduleleaguev2

OUT = Path(__file__).parent
SEASON = "2025-26"
DAYS = ["2026-01-15", "2026-01-16"]
# Games after the recorded days whose status is rewritten to exercise the mapping.
SCHEDULED_SAMPLE = 3


def _records(df) -> list[dict]:
    rows = df.to_dict("records")
    return [
        {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()}
        for row in rows
    ]


def _dump(name: str, data) -> None:
    (OUT / name).write_text(json.dumps(data, indent=1, ensure_ascii=False, default=str))


def main() -> None:
    logged_players: set[int] = set()
    for day in DAYS:
        frame = leaguegamelog.LeagueGameLog(
            season=SEASON,
            player_or_team_abbreviation="P",
            season_type_all_star="Regular Season",
            date_from_nullable=day,
            date_to_nullable=day,
            timeout=30,
        ).get_data_frames()[0]
        rows = _records(frame)
        logged_players |= {r["PLAYER_ID"] for r in rows}
        _dump(f"leaguegamelog_P_{SEASON}_{day}.json", rows)

    schedule = _records(
        scheduleleaguev2.ScheduleLeagueV2(season=SEASON, timeout=30).get_data_frames()[0]
    )
    keep = [g for g in schedule if g["gameDateEst"][:10] in DAYS]
    later = sorted(
        (g for g in schedule if g["gameDateEst"][:10] > DAYS[-1] and g["gameId"][:3] == "002"),
        key=lambda g: g["gameDateEst"],
    )[: SCHEDULED_SAMPLE + 2]
    for g in later[:SCHEDULED_SAMPLE]:
        g["gameStatus"] = 1
    later[SCHEDULED_SAMPLE]["gameStatus"] = 2
    later[SCHEDULED_SAMPLE + 1]["gameStatus"] = 1
    later[SCHEDULED_SAMPLE + 1]["postponedStatus"] = "Y"
    columns = [
        "gameId",
        "gameDateEst",
        "gameStatus",
        "postponedStatus",
        "homeTeam_teamId",
        "awayTeam_teamId",
    ]
    _dump(f"scheduleleaguev2_{SEASON}.json", [{c: g[c] for c in columns} for g in keep + later])

    index = _records(playerindex.PlayerIndex(season=SEASON, timeout=30).get_data_frames()[0])
    _dump(f"playerindex_{SEASON}.json", [p for p in index if p["PERSON_ID"] in logged_players])


if __name__ == "__main__":
    main()
