"""HTTP routes. Thin: validate, call core/tools, serialize (Constitution stack rule)."""

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

from ffmodel.api import schemas
from ffmodel.contract.migrate import current_version
from ffmodel.core.data import get_data_freshness, get_league, get_matchup_state, list_leagues
from ffmodel.core.scenario import Add, Drop, MoveError, Swap
from ffmodel.tools.impact_analysis.analysis import NotFound, analyze
from ffmodel.tools.impact_analysis.picker import list_players
from ffmodel.tools.impact_analysis.settings import AnalysisSettings
from ffmodel.tools.player_analysis import leaderboard as player_analysis
from ffmodel.tools.player_analysis.settings import LeaderboardQuery, PlayerAnalysisSettings

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
            current_matchup=_current_matchup(get_matchup_state(conn, league_id)),
        )


def _current_matchup(state) -> schemas.CurrentMatchup | None:
    if state is None:
        return None
    return schemas.CurrentMatchup(
        week=state.week,
        period_start=state.period_start,
        period_end=state.period_end,
        as_of=state.as_of,
        loaded_at=state.loaded_at,
    )


def _settings(req: schemas.ScenarioRequest) -> AnalysisSettings:
    return AnalysisSettings(
        league_id=req.league_id,
        team_id=req.team_id,
        mode=req.mode,
        window=req.window,
        as_of=req.as_of,
        iterations=req.iterations,
        seed=req.seed,
        fragility=req.fragility,
        focus_opponent_id=req.focus_opponent_id,
    )


def _moves(req: schemas.ScenarioRequest) -> list:
    out = []
    for m in req.moves:
        if m.type == "drop":
            out.append(Drop(m.player_id, team_id=m.team_id))
        elif m.type == "add":
            out.append(Add(m.player_id, team_id=m.team_id))
        else:
            out.append(Swap(acquire_id=m.acquire_id, give_id=m.give_id, team_id=m.team_id))
    return out


def _run(request: Request, fn):
    with _engine(request).connect() as conn:
        try:
            return fn(conn)
        except (NotFound, player_analysis.NotFound) as exc:
            raise HTTPException(404, str(exc)) from exc
        except MoveError as exc:
            detail = schemas.MoveErrorDetail(
                move_index=exc.move_index if exc.move_index is not None else -1,
                code=exc.code,
                message=exc.message,
            )
            raise HTTPException(422, detail.model_dump()) from exc


@router.post(
    "/impact/analyze",
    response_model=schemas.AnalysisResult,
    responses={422: {"description": "Invalid move or settings"}},
)
def impact_analyze(req: schemas.ScenarioRequest, request: Request):
    return _run(request, lambda conn: analyze(conn, _settings(req), _moves(req)))


@router.post("/impact/players", response_model=schemas.PlayerPage)
def impact_players(req: schemas.PlayersRequest, request: Request):
    return _run(
        request,
        lambda conn: list_players(
            conn,
            _settings(req),
            _moves(req),
            query=req.query,
            limit=req.limit,
            offset=req.offset,
            free_agents_only=req.free_agents_only,
        ),
    )


@router.post("/player-analysis/leaderboard", response_model=schemas.Leaderboard)
def player_analysis_leaderboard(req: schemas.LeaderboardRequest, request: Request):
    settings = PlayerAnalysisSettings(
        league_id=req.league_id,
        team_id=req.team_id,
        window=req.window,
        as_of=req.as_of,
        fragility=req.fragility,
    )
    query = LeaderboardQuery(
        evaluate_for=req.evaluate_for, pool=req.pool, top=req.top, min_games=req.min_games
    )
    return _run(request, lambda conn: player_analysis.leaderboard(conn, settings, query))
