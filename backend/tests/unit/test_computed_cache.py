"""The simulation cache (011 research R2): the focus never changes what is simulated."""

from dataclasses import replace

from sqlalchemy import create_engine

from ffmodel.contract.migrate import migrate
from ffmodel.core.scenario import Drop
from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.settings import AnalysisSettings


def test_focus_shares_the_simulation_and_moves_do_not():
    engine = create_engine("sqlite://")
    migrate(engine)
    cache.clear()
    calls = []

    def compute(tag):
        def run():
            calls.append(tag)
            return object()

        return run

    s = AnalysisSettings(league_id=1, team_id=1)
    with engine.connect() as conn:
        a = cache.computed(conn, s, (), compute("a"))
        b = cache.computed(conn, replace(s, focus_opponent_id=2), (), compute("b"))
        c = cache.computed(conn, s, (Drop(7),), compute("c"))
        d = cache.computed(conn, replace(s, window=10), (), compute("d"))
    assert a is b and calls == ["a", "c", "d"]
    assert c is not a and d is not a
    cache.clear()
