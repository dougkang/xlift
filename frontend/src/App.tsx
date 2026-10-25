import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  analyze,
  ApiError,
  getLeague,
  listLeagues,
  type AnalysisResult,
  type LeagueDetail,
  type LeagueSummary,
  type Move,
  type PlayerRow,
  type ScenarioRequest,
} from "./api/client";
import { CategoryCurves } from "./components/CategoryCurves";
import { CategoryTable } from "./components/CategoryTable";
import { Controls, ModeToggle } from "./components/Controls";
import { WithDelta } from "./components/Delta";
import { PlayerPicker } from "./components/PlayerPicker";
import { Radar } from "./components/Radar";
import { DataLine, RecordHeadline } from "./components/RecordHeadline";
import { RecordTable } from "./components/RecordTable";
import { Roster } from "./components/Roster";
import { SwapDialog } from "./components/SwapDialog";
import { useScenario, type Action, type ScenarioState } from "./state/scenario";
import type { HelpContext } from "./help/content";
import { HelpButton } from "./help/HelpButton";
import { HelpProvider } from "./help/HelpProvider";

const DEBOUNCE_MS = 250;

export function toRequest(state: ScenarioState): ScenarioRequest | null {
  const s = state.settings;
  if (s.leagueId === null || s.teamId === null) return null;
  return {
    league_id: s.leagueId,
    team_id: s.teamId,
    mode: s.mode,
    window: s.window,
    fragility: s.fragility,
    moves: state.moves,
  };
}

/** Impact Analysis as a standalone page, with its own session state. */
export default function App() {
  const [state, dispatch] = useScenario();
  return <ImpactAnalysis state={state} dispatch={dispatch} />;
}

/** Impact Analysis (Tool 1). The Shell owns the state, so settings carry over between tools. */
export function ImpactAnalysis({
  state,
  dispatch,
  nav,
}: {
  state: ScenarioState;
  dispatch: (a: Action) => void;
  nav?: ReactNode;
}) {
  const [leagues, setLeagues] = useState<LeagueSummary[]>([]);
  const [league, setLeague] = useState<LeagueDetail | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [moveError, setMoveError] = useState<string | null>(null);
  const [swapTarget, setSwapTarget] = useState<PlayerRow | null>(null);
  const { leagueId, teamId } = state.settings;

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

  // Tactical is the league's current matchup (005): without an imported one, fall back to strategic.
  useEffect(() => {
    if (state.settings.mode === "tactical" && league && !league.current_matchup) {
      dispatch({ type: "setMode", mode: "strategic" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [league, state.settings.mode]);

  const req = useMemo(() => toRequest(state), [state]);
  const reqKey = JSON.stringify(req);

  useEffect(() => {
    if (!req) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setPending(true);
      analyze(req, controller.signal)
        .then((r) => {
          setResult(r);
          setError(null);
        })
        .catch((e: unknown) => {
          if (controller.signal.aborted) return;
          if (e instanceof ApiError && e.moveIndex !== null) {
            // The server rejected a move: drop it and say why; earlier moves stay.
            setMoveError(e.message);
            dispatch({ type: "popMove" });
            return;
          }
          setError(e instanceof ApiError || e instanceof Error ? e.message : String(e));
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

  const addMove = (move: Move) => {
    setMoveError(null);
    // Record the team the move is made for, so it stays with that team after switching.
    dispatch({ type: "addMove", move: { ...move, team_id: teamId } as Move });
  };
  const selectedRoster = result?.rosters.find((r) => r.team_id === teamId) ?? null;
  const selectedArea = result?.radar?.series.find((s) => s.emphasis === "selected")?.area ?? null;
  const helpCtx = useMemo<HelpContext>(
    () => ({
      mode: state.settings.mode,
      iterations: result?.settings.iterations ?? null,
      window: state.settings.window,
      capacity: league?.active_roster_capacity ?? null,
      opponentName: result?.header.matchup?.opponent_name ?? null,
      asOf: league?.current_matchup?.as_of ?? null,
    }),
    [state.settings.mode, state.settings.window, result, league],
  );

  return (
    <HelpProvider ctx={helpCtx}>
      <div className="page">
        {nav}
        <div className="masthead-row">
          <h1 className="masthead">Impact Analysis</h1>
          <ModeToggle
            settings={state.settings}
            league={league}
            dispatch={(a) => {
              setMoveError(null);
              dispatch(a);
            }}
          />
        </div>
        <p className="explainer">
          See how adding, dropping, or swapping players changes your team — this week or for the long run.
          {result &&
            ` Every projection is a Monte Carlo simulation of ${result.settings.iterations.toLocaleString("en-US")} matchup weeks per team.`}
          {result && <DataLine freshness={result.freshness} />}
        </p>
        <hr className="section-rule" />
        <Controls
          leagues={leagues}
          league={league}
          settings={state.settings}
          dispatch={(a) => {
            setMoveError(null);
            dispatch(a);
          }}
          moveCount={state.moves.length}
        />
        <hr className="section-rule" />
        {error && <p className="error" role="alert">{error}</p>}
        {result?.warnings.map((w) => (
          <p key={w.code} className="error" role="status">
            {w.message}
          </p>
        ))}
        {result && <RecordHeadline result={result} pending={pending} />}
        {moveError && (
          <p className="error move-error" role="alert">
            Move not applied: {moveError}
          </p>
        )}
        <div className="layout">
          <main className={pending ? "pending" : undefined}>
            {result && teamId !== null && (
              <>
                {/* A 2x2 grid: the rows are shared, so Per Category Ranking and H2H always start
                    at the same height whatever the radar or roster heights are. */}
                <div className="two-col aligned">
                  <section className="cell-radar">
                    <h3 className="section-divider">
                      Radar <HelpButton topic="radar" />
                    </h3>
                    <div
                      className="radar-scale"
                      role="radiogroup"
                      aria-label="Radar scale"
                      title="Each tab shows your radar's area relative to the league's largest (top team = 100)"
                    >
                      {(["rank", "average", "winrate"] as const).map((sc) => (
                        <button
                          key={sc}
                          className={`pill${state.settings.radarScale === sc ? " active" : ""}`}
                          role="radio"
                          aria-checked={state.settings.radarScale === sc}
                          onClick={() => dispatch({ type: "setRadarScale", scale: sc })}
                        >
                          {{ rank: "Rank", average: "Average", winrate: "Win %" }[sc]}
                          {selectedArea && (
                            <span className="area" aria-label="Radar area score">
                              <WithDelta change={result.changes?.radar.area[sc === "winrate" ? "win_rate" : sc]}>
                                {Math.round(selectedArea[sc === "winrate" ? "win_rate" : sc] * 100)}
                              </WithDelta>
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                    <div className="radar-wrap">
                      <Radar result={result} scale={state.settings.radarScale} />
                    </div>
                  </section>
                  <div className="cell-roster">
                    <Roster result={result} teamId={teamId} onDrop={(id) => addMove({ type: "drop", player_id: id })} />
                  </div>
                  <div className="cell-ranking">
                    <CategoryTable result={result} />
                  </div>
                  <div className="cell-h2h">
                    {/* Tactical: the opponent's roster replaces H2H, read-only (005 FR-016). */}
                    {result.header.matchup ? (
                      <Roster
                        result={result}
                        teamId={result.header.matchup.opponent_id}
                        title={result.header.matchup.opponent_name}
                        helpTopic="opponentRoster"
                      />
                    ) : (
                      <RecordTable result={result} />
                    )}
                  </div>
                </div>
                <CategoryCurves result={result} />
              </>
            )}
          </main>
          <aside className="sidebar">
            <h3 className="section-divider">
              Players <HelpButton topic="players" />
            </h3>
            {req && swapTarget && selectedRoster && (
              <SwapDialog
                target={swapTarget}
                roster={selectedRoster}
                request={req}
                onCancel={() => setSwapTarget(null)}
                onConfirm={(giveId) => {
                  addMove({ type: "swap", acquire_id: swapTarget.player_id, give_id: giveId });
                  setSwapTarget(null);
                }}
              />
            )}
            {req && (
              <PlayerPicker
                request={req}
                onAdd={(id) => addMove({ type: "add", player_id: id })}
                onSwap={setSwapTarget}
              />
            )}
          </aside>
        </div>
      </div>
    </HelpProvider>
  );
}
