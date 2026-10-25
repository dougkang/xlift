"""Record Impact Analysis's pre-009 numbers for SC-007 (009 tasks T002).

Run once on the pre-feature code: `uv run pytest -m snapshot`. The normal run skips it;
`test_leaderboard.py` compares against the file it writes.
"""

import json
from pathlib import Path

import pytest

from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.analysis import analyze
from ffmodel.tools.impact_analysis.picker import list_players
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from tests.fixtures import impact_dataset as fx

PRE009 = Path(__file__).resolve().parents[1] / "fixtures" / "pre009_impact.json"


def impact_numbers(conn) -> dict:
    """Impact Analysis's strategic analysis and picker for the fixture's first team."""
    s = AnalysisSettings(league_id=1, team_id=1, as_of=fx.IMPACT_TODAY)
    r = analyze(conn, s)
    page = list_players(conn, s, limit=200)
    got = {k: r[k] for k in ("header", "category_table", "rosters")}
    got["players"] = [[p["player_id"], p["xlift"]] for p in page["players"]]
    return json.loads(json.dumps(got, default=str, sort_keys=True))


@pytest.mark.snapshot
def test_record_pre009(impact_engine):
    cache.clear()
    with impact_engine.connect() as conn:
        PRE009.write_text(json.dumps(impact_numbers(conn), indent=1, sort_keys=True) + "\n")
