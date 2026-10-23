"""HTTP routes. Thin: validate, call core/tools, serialize (Constitution stack rule)."""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

from ffmodel.api import schemas
from ffmodel.contract.migrate import current_version
from ffmodel.core.data import get_data_freshness, get_league, list_leagues
from ffmodel.tools.impact_analysis.analysis import NotFound, analyze
from ffmodel.tools.impact_analysis.settings import AnalysisSettings

router = APIRouter(prefix="/api")


def _engine(request: Request):
    return request.app.state.engine


def _team_count(conn, league_id: int) -> int:
    return conn.execute(
        text("SELECT COUNT(*) FROM fantasy_team WHERE league_id = :l"), {"l": league_id}
    ).scalar_one()


@router.get("/health")
def health(request: Request) -> dict:
    return {"status": "ok", "schema_version": current_version(_engine(request))}


@router.get("/leagues", response_model=list[schemas.LeagueSummary])
def leagues(request: Request):
    with _engine(request).connect() as conn:
        return [
            schemas.LeagueSummary(**s.__dict__, team_count=_team_count(conn, s.league_id))
            for s in list_leagues(conn)
        ]


@router.get("/leagues/{league_id}", response_model=schemas.LeagueDetail)
def league_detail(league_id: int, request: Request):
    with _engine(request).connect() as conn:
        found = [s for s in list_leagues(conn) if s.league_id == league_id]
        if not found:
            raise HTTPException(404, f"no league {league_id}")
        snap = get_league(conn, league_id)
        fresh = get_data_freshness(conn, league_id)
        return schemas.LeagueDetail(
            **found[0].__dict__,
            team_count=len(snap.teams),
            teams=[
                schemas.TeamSummary(
                    team_id=t.fantasy_team_id,
                    source_team_key=t.source_team_key,
                    name=t.name,
                    manager=t.manager,
                )
                for t in snap.teams
            ],
            freshness=schemas.Freshness(**fresh.__dict__),
        )


def _settings(req: schemas.ScenarioRequest) -> AnalysisSettings:
    return AnalysisSettings(
        league_id=req.league_id,
        team_id=req.team_id,
        mode=req.mode,
        window=req.window,
        as_of=req.as_of,
        opponent_id=req.opponent_id,
        period_start=req.period_start,
        period_end=req.period_end,
        iterations=req.iterations,
        seed=req.seed,
    )


@router.post("/impact/analyze", response_model=schemas.AnalysisResult)
def impact_analyze(req: schemas.ScenarioRequest, request: Request):
    with _engine(request).connect() as conn:
        try:
            return analyze(conn, _settings(req), req.moves)
        except NotFound as exc:
            raise HTTPException(404, str(exc)) from exc
