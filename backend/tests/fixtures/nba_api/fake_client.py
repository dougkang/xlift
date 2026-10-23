"""Serves recorded nba_api responses with the NbaStatsClient interface (tasks.md T018)."""

import copy
import json
from pathlib import Path

HERE = Path(__file__).parent


def _read(name: str) -> list[dict]:
    return json.loads((HERE / name).read_text())


class FakeNbaStatsClient:
    def __init__(self, log_days=("2026-01-15", "2026-01-16")):
        self.logs = []
        for day in log_days:
            self.logs += _read(f"leaguegamelog_P_2025-26_{day}.json")
        self.sched = _read("scheduleleaguev2_2025-26.json")
        self.index = _read("playerindex_2025-26.json")
        self.calls: list[tuple] = []

    def game_log(self, season, date_from=None):
        self.calls.append(("game_log", season, date_from))
        rows = [r for r in self.logs if date_from is None or r["GAME_DATE"] >= date_from]
        return copy.deepcopy(rows)

    def schedule(self, season):
        self.calls.append(("schedule", season))
        return copy.deepcopy(self.sched)

    def player_index(self, season):
        self.calls.append(("player_index", season))
        return copy.deepcopy(self.index)
