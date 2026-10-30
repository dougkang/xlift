import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  getLeague,
  leaderboard,
  listLeagues,
  type Leaderboard as LeaderboardResult,
  type LeaderboardRequest,
  type LeagueDetail,
  type LeagueSummary,
} from "../api/client";
import { Controls } from "../components/Controls";
import { DataLine } from "../components/RecordHeadline";
import type { HelpContext } from "../help/content";
import { HelpButton } from "../help/HelpButton";
import { HelpProvider } from "../help/HelpProvider";
import {
  MIN_GAMES_OPTIONS,
  TOP_OPTIONS,
  usePlayerAnalysis,
  type Pool,
} from "../state/playerAnalysis";
import type { Action, ScenarioState } from "../state/scenario";
import { Leaderboard } from "./Leaderboard";

const DEBOUNCE_MS = 250;
// Player Analysis only changes the settings it shares with Impact Analysis: never moves or mode.
const SHARED_ACTIONS: Action["type"][] = ["setLeague", "setTeam", "setWindow", "setFragility"];

// The Evaluate for dropdown's league option; the other options are team ids.
const LEAGUE = "league";
const POOLS: [Pool, string][] = [
  ["free_agents", "Free agents"],
  ["all", "All players"],
];

/** The pool to ask for: a team that isn't in this league falls back to free agents. */
function effectivePool(pool: Pool, league: LeagueDetail | null): Pool {
  if (typeof pool !== "number") return pool;
  return league?.teams.some((t) => t.team_id === pool) ? pool : "free_agents";
}

/** Player Analysis (Tool 2), 009: the xLift leaderboard (contracts/ui.md "Page"). */
export function PlayerAnalysis({
  state,
  dispatch,
  nav,
}: {
  state: ScenarioState;
  dispatch: (a: Action) => void;
  nav?: ReactNode;
}) {
  const [board, setBoard] = usePlayerAnalysis();
  const [leagues, setLeagues] = useState<LeagueSummary[]>([]);
  const [league, setLeague] = useState<LeagueDetail | null>(null);
  const [result, setResult] = useState<LeaderboardResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { leagueId, teamId, window, fragility } = state.settings;
  const share = (a: Action) => {
    if (SHARED_ACTIONS.includes(a.type)) dispatch(a);
  };

  useEffect(() => {
    listLeagues()
      .then((ls) => {
        setLeagues(ls);
        if (leagueId === null && ls.length) dispatch({ type: "setLeague", leagueId: ls[0].league_id });
      })
      .catch((e: Error) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (leagueId === null) return;
    getLeague(leagueId)
      .then((l) => {
        setLeague(l);
        if (teamId === null && l.teams.length) dispatch({ type: "setTeam", teamId: l.teams[0].team_id });
      })
      .catch((e: Error) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leagueId]);

  const pool = effectivePool(board.pool, league);
  const req = useMemo<LeaderboardRequest | null>(
    () =>
      leagueId === null || teamId === null || (typeof board.pool === "number" && !league)
        ? null
        : {
            league_id: leagueId,
            team_id: teamId,
            window,
            fragility,
            evaluate_for: board.evaluateFor,
            pool,
            top: board.top,
            min_games: board.minGames,
          },
    [leagueId, teamId, window, fragility, board, pool, league],
  );
  const reqKey = JSON.stringify(req);

  useEffect(() => {
    if (!req) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setPending(true);
      leaderboard(req, controller.signal)
        .then((r) => {
          setResult(r);
          setError(null);
        })
        .catch((e: unknown) => {
          if (!controller.signal.aborted) setError(e instanceof Error ? e.message : String(e));
        })
        .finally(() => {
          if (!controller.signal.aborted) setPending(false);
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reqKey]);

  const helpCtx = useMemo<HelpContext>(
    () => ({
      mode: "strategic",
      iterations: null,
      window,
      capacity: league?.active_roster_capacity ?? null,
      opponentName: null,
      asOf: null,
    }),
    [window, league],
  );
  const scope =
    result &&
    (result.evaluate_for === "league" ? "Averaged over every team but the player's own" : `Scored for ${result.team_name}`);
  const footnotes = result?.entries.filter((e) => e.footnote) ?? [];

  return (
    <HelpProvider ctx={helpCtx}>
      <div className="page player-analysis">
        {nav}
        <div className="masthead-row">
          <h1 className="masthead">Player Analysis</h1>
        </div>
        <p className="explainer">
          Find the players worth adding: who adds the most weekly category wins, and in which categories.
          {league && <DataLine freshness={league.freshness} matchup={false} />}
        </p>
        <hr className="section-rule" />
        <Controls
          leagues={leagues}
          league={league}
          settings={state.settings}
          dispatch={share}
          showReset={false}
          showTeam={false}
          helpTopic="playerAnalysisSettings"
          stacked
        />
        <div className="controls leaderboard-controls" role="group" aria-label="Leaderboard settings">
          <div className="controls-row">
            <label>
              <span className="col-header">Evaluate for</span>
              {/* One choice for whose position scores the players: a team (also the team shared with
                  Impact Analysis) or the whole league. */}
              <select
                value={board.evaluateFor === "league" ? LEAGUE : (teamId ?? "")}
                disabled={!league}
                onChange={(e) => {
                  if (e.target.value === LEAGUE) {
                    setBoard({ type: "setEvaluateFor", evaluateFor: "league" });
                    return;
                  }
                  share({ type: "setTeam", teamId: Number(e.target.value) });
                  setBoard({ type: "setEvaluateFor", evaluateFor: "team" });
                }}
              >
                <option value="" disabled>
                  Choose…
                </option>
                <option value={LEAGUE}>League</option>
                {league?.teams.map((t) => (
                  <option key={t.team_id} value={t.team_id}>
                    {t.name} — {t.manager}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="controls-row">
            <label>
              <span className="col-header">Pool</span>
              {/* Free agents, everyone, or one team's players. The team being evaluated for lists
                  its own roster, each player valued against its weakest, as in Impact Analysis. */}
              <select
                value={String(pool)}
                onChange={(e) => {
                  const v = e.target.value;
                  setBoard({ type: "setPool", pool: v === "free_agents" || v === "all" ? v : Number(v) });
                }}
              >
                {POOLS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
                {league?.teams.map((t) => (
                  <option key={t.team_id} value={t.team_id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="controls-row">
            <label>
              <span className="col-header">Show top</span>
              <select value={board.top} onChange={(e) => setBoard({ type: "setTop", top: Number(e.target.value) })}>
                {TOP_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="controls-row">
            <label>
              <span className="col-header">Min games</span>
              <select
                value={board.minGames}
                onChange={(e) => setBoard({ type: "setMinGames", minGames: Number(e.target.value) })}
              >
                {MIN_GAMES_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        {state.moves.length > 0 && (
          <p className="moves-note">The leaderboard uses rosters as they are, without your Impact Analysis moves.</p>
        )}
        <hr className="section-rule" />
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {result?.warnings.map((w) => (
          <p key={w.code} className="error" role="status">
            {w.message}
          </p>
        ))}
        <section className={pending ? "pending" : undefined}>
          <h3 className="section-divider">
            xLift Leaderboard <HelpButton topic="leaderboard" />
          </h3>
          {result && (
            <>
              <p className="scope-line">
                {scope} · {result.entries.length} of {result.total} players
              </p>
              <Leaderboard categories={result.categories} entries={result.entries} />
              {footnotes.length > 0 && (
                <ul className="footnotes">
                  {footnotes.map((e) => (
                    <li key={e.player_id}>
                      {e.footnote} — {e.name}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </section>
      </div>
    </HelpProvider>
  );
}
