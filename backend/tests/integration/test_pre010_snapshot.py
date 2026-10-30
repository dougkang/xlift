"""Record Impact Analysis's pre-010 results for SC-004 (010 tasks T001).

Run once on the pre-feature code: `uv run pytest -m snapshot -k pre010`.
The normal run skips it; `test_pre010_regression.py` compares against the file it writes.
"""

import json
from pathlib import Path

import pytest

from ffmodel.core.scenario import Drop
from ffmodel.tools.impact_analysis import cache
from ffmodel.tools.impact_analysis.analysis import analyze
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from tests.fixtures import impact_dataset as fx

PRE010 = Path(__file__).resolve().parents[1] / "fixtures" / "pre010_impact.json"
GAMMAS = 3


def impact_results(conn) -> dict:
    """Full strategic and tactical results for the Gammas, with and without a drop."""
    out = {}
    for mode in ("strategic", "tactical"):
        s = AnalysisSettings(
            league_id=1, team_id=GAMMAS, mode=mode, as_of=fx.IMPACT_TODAY, iterations=1000
        )
        for label, moves in (("base", ()), ("moved", (Drop(fx.GAMMA_1),))):
            cache.clear()
            out[f"{mode}_{label}"] = analyze(conn, s, moves)
    return json.loads(json.dumps(out, default=str, sort_keys=True))


@pytest.mark.snapshot
def test_record_pre010(impact_engine):
    with impact_engine.begin() as conn:
        fx.load_matchup_state(conn, as_of=fx.IMPACT_TODAY)
    with impact_engine.connect() as conn:
        PRE010.write_text(json.dumps(impact_results(conn), indent=1, sort_keys=True) + "\n")
