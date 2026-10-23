"""Paced, retrying access to the NBA stats source (research R5)."""

import math
import time
from collections.abc import Callable

import requests

RETRY_STATUS = {429, 500, 502, 503, 504}
BACKOFF = (2, 4, 8, 16, 32)


class SourceUnavailable(RuntimeError):
    pass


def _default_endpoints() -> dict[str, Callable]:
    from nba_api.stats.endpoints import leaguegamelog, playerindex, scheduleleaguev2

    return {
        "game_log": leaguegamelog.LeagueGameLog,
        "schedule": scheduleleaguev2.ScheduleLeagueV2,
        "player_index": playerindex.PlayerIndex,
    }


def _records(frame) -> list[dict]:
    return [
        {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()}
        for row in frame.to_dict("records")
    ]


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, requests.exceptions.HTTPError):
        return exc.response is not None and exc.response.status_code in RETRY_STATUS
    return isinstance(exc, requests.exceptions.Timeout | requests.exceptions.ConnectionError)


class NbaStatsClient:
    def __init__(
        self,
        min_interval: float = 1.0,
        timeout: int = 30,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        endpoints: dict[str, Callable] | None = None,
    ):
        self.min_interval = min_interval
        self.timeout = timeout
        self._sleep = sleep
        self._clock = clock
        self._endpoints = endpoints
        self._last_call: float | None = None

    def _call(self, name: str, **params) -> list[dict]:
        endpoints = self._endpoints or _default_endpoints()
        self._endpoints = endpoints
        for attempt in range(len(BACKOFF) + 1):
            if self._last_call is not None:
                wait = self.min_interval - (self._clock() - self._last_call)
                if wait > 0:
                    self._sleep(wait)
            self._last_call = self._clock()
            try:
                frame = endpoints[name](timeout=self.timeout, **params).get_data_frames()[0]
                return _records(frame)
            except Exception as exc:
                if not _retryable(exc):
                    raise
                if attempt == len(BACKOFF):
                    raise SourceUnavailable(f"{name} failed after {attempt + 1} attempts") from exc
                self._sleep(BACKOFF[attempt])
        raise AssertionError("unreachable")

    def game_log(self, season: str, date_from: str | None = None) -> list[dict]:
        return self._call(
            "game_log",
            season=season,
            player_or_team_abbreviation="P",
            season_type_all_star="Regular Season",
            date_from_nullable=date_from or "",
        )

    def schedule(self, season: str) -> list[dict]:
        return self._call("schedule", season=season)

    def player_index(self, season: str) -> list[dict]:
        return self._call("player_index", season=season)
