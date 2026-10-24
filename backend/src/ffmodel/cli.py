"""`ffm` command line (contracts/cli.md). The only module that wires adapters and core together."""

import json
import sys
from datetime import date
from typing import Annotated

import typer
from sqlalchemy import text

from ffmodel.contract.db import get_engine
from ffmodel.contract.migrate import current_version, migrate

app = typer.Typer(no_args_is_help=True, help="FF-Model data tools.")
db_app = typer.Typer(no_args_is_help=True, help="Schema management.")
load_app = typer.Typer(no_args_is_help=True, help="Load data into the contract.")
app.add_typer(db_app, name="db")
app.add_typer(load_app, name="load")

state = {"json": False}


@app.callback()
def main(as_json: Annotated[bool, typer.Option("--json", help="Machine-readable output.")] = False):
    state["json"] = as_json


def _emit(payload: dict, human: str) -> None:
    typer.echo(json.dumps(payload, default=str) if state["json"] else human)


def _summary_text(summary) -> str:
    lines = [f"run {summary.run_id}: {summary.outcome}"]
    for table in sorted(set(summary.inserted) | set(summary.updated)):
        lines.append(
            f"  {table:<20} +{summary.inserted.get(table, 0):>6}"
            f"  ~{summary.updated.get(table, 0):>6}"
        )
    d = summary.details
    if d:
        lines.append(f"  week {d['week']}  {d['period'][0]} → {d['period'][1]}  as of {d['as_of']}")
        lines += [f"  {a}  vs  {b}" for a, b in d["pairings"]]
    if summary.replaced:
        lines.append(f"  replaced the previous matchup state ({summary.replaced} teams)")
    if summary.report:
        lines.append(summary.report)
    return "\n".join(lines)


def _summary_payload(summary) -> dict:
    return {
        "run_id": summary.run_id,
        "outcome": summary.outcome,
        "inserted": summary.inserted,
        "updated": summary.updated,
        "report": summary.report,
        **({"details": summary.details} if summary.details else {}),
    }


def _engine():
    engine = get_engine()
    migrate(engine)
    return engine


@db_app.command("migrate")
def db_migrate():
    """Apply pending migrations."""
    applied = migrate(get_engine())
    _emit({"applied": applied}, f"applied: {applied or 'none'}")


@db_app.command("version")
def db_version():
    """Print the current schema version."""
    version = current_version(get_engine())
    _emit({"version": version}, str(version))


@load_app.command("nba")
def load_nba_cmd(
    season: Annotated[list[str] | None, typer.Option("--season", help="e.g. 2026-27")] = None,
    full: Annotated[bool, typer.Option("--full", help="Ignore the incremental cursor.")] = False,
):
    """Load regular-season NBA data from nba_api (FR-012)."""
    from ffmodel.adapters.nba_stats.loader import load_nba

    try:
        summary = load_nba(_engine(), seasons=season or None, full=full)
    except Exception as exc:
        typer.echo(f"load failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    _emit(_summary_payload(summary), _summary_text(summary))


roster_app = typer.Typer(no_args_is_help=True, help="Roster matching.")
app.add_typer(roster_app, name="roster")


@load_app.command("roster")
def load_roster_cmd(
    path: Annotated[str, typer.Argument(help="Roster CSV export.")],
    league_key: Annotated[str, typer.Option("--league-key")],
    name: Annotated[str | None, typer.Option("--name")] = None,
    season: Annotated[str | None, typer.Option("--season")] = None,
    scoring_format: Annotated[str | None, typer.Option("--format")] = None,
    capacity: Annotated[int | None, typer.Option("--capacity")] = None,
    source: Annotated[str, typer.Option("--source")] = "yahoo",
    as_of: Annotated[
        str | None,
        typer.Option(
            "--as-of",
            help="YYYY-MM-DD; defaults to the file's modified date (before noon: the day before)",
        ),
    ] = None,
):
    """Load a roster file into a league (all-or-nothing)."""
    from ffmodel.adapters.roster_csv.loader import load_roster

    try:
        summary = load_roster(
            _engine(),
            path,
            league_key,
            name=name,
            season=season,
            scoring_format=scoring_format,
            capacity=capacity,
            source=source,
            as_of=_parse_date(as_of),
        )
    except Exception as exc:
        typer.echo(f"load failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    _emit(_summary_payload(summary), _summary_text(summary))
    if summary.outcome == "rejected":
        raise typer.Exit(2)


@load_app.command("matchups")
def load_matchups_cmd(
    path: Annotated[str, typer.Argument(help="matchups.csv export (week-to-date team totals).")],
    league_key: Annotated[str, typer.Option("--league-key")],
    as_of: Annotated[
        str | None,
        typer.Option(
            "--as-of",
            help="YYYY-MM-DD; defaults to the file's modified date (before noon: the day before)",
        ),
    ] = None,
    period_start: Annotated[
        str | None, typer.Option("--period-start", help="defaults to the as-of week's Monday")
    ] = None,
    period_end: Annotated[
        str | None, typer.Option("--period-end", help="defaults to the as-of week's Sunday")
    ] = None,
):
    """Load the league's current matchup state (all-or-nothing; replaces the previous one)."""
    from ffmodel.adapters.matchup_csv.loader import load_matchups

    try:
        summary = load_matchups(
            _engine(),
            path,
            league_key,
            as_of=_parse_date(as_of),
            period_start=_parse_date(period_start),
            period_end=_parse_date(period_end),
        )
    except Exception as exc:
        typer.echo(f"load failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    _emit(_summary_payload(summary), _summary_text(summary))
    if summary.outcome == "rejected":
        raise typer.Exit(2)


@roster_app.command("resolve")
def roster_resolve(
    external_id: Annotated[str, typer.Argument()],
    player_id: Annotated[int, typer.Argument(help="Internal player_id (shown in brackets).")],
    source: Annotated[str, typer.Option("--source")] = "yahoo",
):
    """Confirm a roster row's player; reused on every later load."""
    from ffmodel.adapters.roster_csv.loader import resolve_match

    try:
        resolve_match(_engine(), source, external_id, player_id)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    _emit(
        {"source": source, "external_id": external_id, "player_id": player_id},
        f"{source}:{external_id} -> {player_id}",
    )


@app.command("runs")
def runs(limit: Annotated[int, typer.Option("--limit")] = 10):
    """Recent load runs."""
    with _engine().connect() as conn:
        rows = (
            conn.execute(
                text(
                    "SELECT run_id, source, scope, outcome, rows_inserted, rows_updated,"
                    " finished_at"
                    " FROM load_run ORDER BY run_id DESC LIMIT :n"
                ),
                {"n": limit},
            )
            .mappings()
            .all()
        )
    _emit(
        {"runs": [dict(r) for r in rows]},
        "\n".join(
            f"{r['run_id']:>4}  {r['source']:<10} {r['outcome']:<9} +{r['rows_inserted']:<6}"
            f" ~{r['rows_updated']:<6} {r['finished_at'] or '-'}  {r['scope']}"
            for r in rows
        )
        or "no runs",
    )


players_app = typer.Typer(no_args_is_help=True, help="Player lookup.")
app.add_typer(players_app, name="players")


@players_app.command("search")
def players_search(
    query: Annotated[str, typer.Argument()],
    limit: Annotated[int, typer.Option("--limit")] = 25,
):
    """Accent-insensitive player search."""
    from ffmodel.core.data import search_players

    with _engine().connect() as conn:
        found = search_players(conn, query, limit=limit)
    _emit(
        {"players": [p.__dict__ for p in found]},
        "\n".join(
            f"[{p.player_id}] {p.full_name} ({p.current_team or '-'}) {','.join(p.positions)}"
            for p in found
        )
        or "no matches",
    )


@app.command("serve")
def serve(
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port")] = 8000,
    reload: Annotated[bool, typer.Option("--reload")] = False,
):
    """Run the API (and the built frontend, if present)."""
    import uvicorn

    uvicorn.run("ffmodel.api.app:create_app", factory=True, host=host, port=port, reload=reload)


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


if __name__ == "__main__":
    sys.exit(app())
