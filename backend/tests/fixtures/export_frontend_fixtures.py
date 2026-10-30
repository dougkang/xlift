"""Write real API responses for frontend tests (002 tasks.md T039).

Run: cd backend && uv run python -m tests.fixtures.export_frontend_fixtures
"""

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text

from ffmodel.api.app import create_app
from ffmodel.contract.db import get_engine
from ffmodel.contract.migrate import migrate
from tests.fixtures import impact_dataset as fx
from tests.fixtures.impact_dataset import load_impact_fixture

OUT = Path(__file__).resolve().parents[3] / "frontend" / "tests" / "fixtures"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        engine = get_engine(f"sqlite:///{tmp}/export.sqlite")
        migrate(engine)
        with engine.begin() as conn:
            load_impact_fixture(conn)
            # Give Deltas a short-history player so the fixture carries a footnote.
            conn.execute(
                text("UPDATE roster_entry SET player_id = :r WHERE player_id = :d"),
                {"r": fx.ROOKIE, "d": fx.DELTA_3},
            )
            # The current matchup (005), captured the same day as the rosters: Gammas play Deltas.
            fx.load_matchup_state(conn, as_of=fx.IMPACT_TODAY)
        client = TestClient(create_app(engine))
        body = {
            "league_id": 1,
            "team_id": 4,
            "as_of": fx.IMPACT_TODAY.isoformat(),
            "iterations": 2000,
        }
        res = client.post("/api/impact/analyze", json=body)
        res.raise_for_status()
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "strategic.json").write_text(json.dumps(res.json(), indent=1))
        tactical = client.post(
            "/api/impact/analyze",
            json={
                "league_id": 1,
                "team_id": 3,
                "mode": "tactical",
                "as_of": fx.IMPACT_TODAY.isoformat(),
                "iterations": 2000,
            },
        )
        tactical.raise_for_status()
        (OUT / "tactical.json").write_text(json.dumps(tactical.json(), indent=1))
        moves = client.post(
            "/api/impact/analyze",
            json={
                "league_id": 1,
                "team_id": 4,
                "as_of": fx.IMPACT_TODAY.isoformat(),
                "iterations": 2000,
                # Deltas trade for Alpha One: +1 win and an L -> W flip against Alphas.
                "moves": [
                    {"type": "swap", "acquire_id": fx.ALPHA_1, "give_id": fx.DELTA_1, "team_id": 4}
                ],
            },
        )
        moves.raise_for_status()
        (OUT / "strategic_moves.json").write_text(json.dumps(moves.json(), indent=1))
        tactical_moves = client.post(
            "/api/impact/analyze",
            json={
                "league_id": 1,
                "team_id": 3,
                "mode": "tactical",
                "as_of": fx.IMPACT_TODAY.isoformat(),
                "iterations": 2000,
                # Gammas trade with their opponent Deltas: both teams change.
                "moves": [
                    {"type": "swap", "acquire_id": fx.DELTA_1, "give_id": fx.GAMMA_2, "team_id": 3}
                ],
            },
        )
        tactical_moves.raise_for_status()
        (OUT / "tactical_moves.json").write_text(json.dumps(tactical_moves.json(), indent=1))
        (OUT / "league.json").write_text(json.dumps(client.get("/api/leagues/1").json(), indent=1))
        (OUT / "leagues.json").write_text(json.dumps(client.get("/api/leagues").json(), indent=1))
        # The same league scored H2H Each Category (010): the strategic view, with the Deltas'
        # trade, and the tactical view.
        with engine.begin() as conn:
            conn.execute(text("UPDATE fantasy_league SET scoring_format_id = '9cat_h2h_each'"))
        for name, req in (
            ("strategic_each", body),
            ("strategic_each_moves", moves.request),
            ("tactical_each", tactical.request),
        ):
            payload = req if isinstance(req, dict) else json.loads(req.content)
            res = client.post("/api/impact/analyze", json=payload)
            res.raise_for_status()
            (OUT / f"{name}.json").write_text(json.dumps(res.json(), indent=1))
        engine.dispose()


if __name__ == "__main__":
    main()
