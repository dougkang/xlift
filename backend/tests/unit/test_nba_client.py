import pytest
import requests

from ffmodel.adapters.nba_stats.client import NbaStatsClient, SourceUnavailable


class Frame:
    def to_dict(self, orient):
        return [{"A": 1, "B": float("nan")}]


class Endpoint:
    def __init__(self, failures):
        self.failures = list(failures)
        self.kwargs = []

    def __call__(self, **kwargs):
        self.kwargs.append(kwargs)
        if self.failures:
            raise self.failures.pop(0)
        return self

    def get_data_frames(self):
        return [Frame()]


class Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def __call__(self):
        return self.now


def http_error(status):
    resp = requests.Response()
    resp.status_code = status
    return requests.exceptions.HTTPError(response=resp)


def make(failures=()):
    clock = Clock()
    ep = Endpoint(failures)
    client = NbaStatsClient(
        sleep=clock.sleep,
        clock=clock,
        endpoints={"schedule": ep, "game_log": ep, "player_index": ep},
    )
    return client, ep, clock


def test_pacing_and_timeout():
    client, ep, clock = make()
    assert client.schedule("2025-26") == [{"A": 1, "B": None}]
    client.schedule("2025-26")
    assert clock.sleeps == [1.0]
    assert all(k["timeout"] == 30 for k in ep.kwargs)


def test_retries_then_succeeds():
    client, ep, clock = make([requests.exceptions.ReadTimeout(), http_error(503)])
    client.player_index("2025-26")
    assert clock.sleeps[:1] == [2] and 4 in clock.sleeps
    assert len(ep.kwargs) == 3


def test_retries_exhausted():
    client, _, clock = make([requests.exceptions.ConnectionError()] * 6)
    with pytest.raises(SourceUnavailable):
        client.schedule("2025-26")
    assert [s for s in clock.sleeps if s >= 2] == [2, 4, 8, 16, 32]


def test_non_retryable_raises_immediately():
    client, ep, _ = make([http_error(400)])
    with pytest.raises(requests.exceptions.HTTPError):
        client.schedule("2025-26")
    assert len(ep.kwargs) == 1


def test_game_log_params():
    client, ep, _ = make()
    client.game_log("2025-26", "2026-01-12")
    assert ep.kwargs[0]["season_type_all_star"] == "Regular Season"
    assert ep.kwargs[0]["date_from_nullable"] == "2026-01-12"
    assert ep.kwargs[0]["player_or_team_abbreviation"] == "P"
