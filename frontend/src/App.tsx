import { useEffect, useMemo, useState } from "react";
import {
  analyze,
  ApiError,
  getLeague,
  listLeagues,
  type AnalysisResult,
  type LeagueDetail,
  type LeagueSummary,
  type ScenarioRequest,
} from "./api/client";
import { CategoryCurves } from "./components/CategoryCurves";
import { CategoryTable } from "./components/CategoryTable";
import { Controls } from "./components/Controls";
import { Radar } from "./components/Radar";
import { DataLine, RecordHeadline } from "./components/RecordHeadline";
import { RecordTable } from "./components/RecordTable";
import { Roster } from "./components/Roster";
import { useScenario, type ScenarioState } from "./state/scenario";

const DEBOUNCE_MS = 250;

export function toRequest(state: ScenarioState): ScenarioRequest | null {
  const s = state.settings;
  if (s.leagueId === null || s.teamId === null) return null;
  return {
    league_id: s.leagueId,
    team_id: s.teamId,
    mode: s.mode,
    window: s.window,
    opponent_id: s.mode === "tactical" ? s.opponentId : null,
    period_start: s.mode === "tactical" ? s.periodStart : null,
    period_end: s.mode === "tactical" ? s.periodEnd : null,
    moves: state.moves,
  };
}

export default function App() {
  const [state, dispatch] = useScenario();
  const [leagues, setLeagues] = useState<LeagueSummary[]>([]);
  const [league, setLeague] = useState<LeagueDetail | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
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

  return (
    <div className="page">
      <h1 className="masthead">Impact Analysis</h1>
      <p className="explainer">
        See how adding, dropping, or swapping players changes your team — this week or for the long run.
      </p>
      <Controls leagues={leagues} league={league} settings={state.settings} dispatch={dispatch} />
      {result && <DataLine result={result} />}
      {error && <p className="error" role="alert">{error}</p>}
      {result?.warnings.map((w) => (
        <p key={w.code} className="error" role="status">
          {w.message}
        </p>
      ))}
      {result && <RecordHeadline result={result} pending={pending} />}
      <div className="layout">
        <main className={pending ? "pending" : undefined}>
          {result && teamId !== null && (
            <>
              <div className="two-col">
                <section>
                  <h3 className="section-divider">Category Ranks</h3>
                  <div className="radar-wrap">
                    <Radar result={result} />
                    <CategoryTable result={result} />
                  </div>
                </section>
                <div>
                  <Roster result={result} teamId={teamId} />
                  <RecordTable result={result} />
                </div>
              </div>
              <CategoryCurves result={result} />
            </>
          )}
        </main>
        <aside className="sidebar">
          <h3 className="section-divider">Players</h3>
          <p className="col-header">Player picker arrives with roster moves.</p>
        </aside>
      </div>
    </div>
  );
}
