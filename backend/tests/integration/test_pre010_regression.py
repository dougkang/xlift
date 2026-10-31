"""SC-004 (010): most-categories results are identical to the pre-010 code's."""

import json

from tests.fixtures import impact_dataset as fx
from tests.integration.test_pre010_snapshot import PRE010, impact_results
from tests.pre010 import strip_010


def test_most_categories_results_unchanged(impact_engine):
    with impact_engine.begin() as conn:
        fx.load_matchup_state(conn, as_of=fx.IMPACT_TODAY)
    with impact_engine.connect() as conn:
        got = impact_results(conn)
    want = json.loads(PRE010.read_text())
    assert got.keys() == want.keys()
    for key in want:
        g, w = strip_010(got[key]), want[key]
        g.pop("freshness"), w.pop("freshness")  # load timestamps differ per run
        assert g == w, key
        assert got[key]["standings"] == "matchup"
