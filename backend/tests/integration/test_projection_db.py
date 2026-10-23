from datetime import date

from ffmodel.core.model import build_projections
from ffmodel.core.scoring import get_format
from tests.fixtures import dataset as fx

FMT = get_format("9cat_h2h")


def test_projections_from_fixture(fixture_engine):
    with fixture_engine.connect() as conn:
        p = build_projections(
            conn, [fx.IGGY, fx.DONCIC, fx.DYBANTSA], FMT, window=15, as_of=fx.FIXTURE_TODAY
        )
    assert p[fx.IGGY].availability == 0.5  # 2 played of 4 team finals since his window began
    assert p[fx.DONCIC].games_found == 15 and not p[fx.DONCIC].is_short
    assert p[fx.DYBANTSA].is_short and p[fx.DYBANTSA].games_found == 3


def test_games_remaining(fixture_engine):
    with fixture_engine.connect() as conn:
        p = build_projections(
            conn,
            [fx.IGGY],
            FMT,
            window=15,
            as_of=date(2026, 10, 31),
            period=(date(2026, 10, 31), date(2026, 11, 8)),
        )
    assert p[fx.IGGY].games_remaining == 3
