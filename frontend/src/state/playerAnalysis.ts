import { useEffect, useReducer } from "react";

/** Player Analysis's own settings (009 data-model.md "Frontend state"). League, team, window and
 * Fragility Penalty are shared with Impact Analysis (state/scenario.ts). */
export type EvaluateFor = "team" | "league";
/** Free agents, everyone, or one fantasy team's players (its team id). */
export type Pool = "free_agents" | "all" | number;

export interface LeaderboardSettings {
  evaluateFor: EvaluateFor;
  pool: Pool;
  top: number;
  minGames: number;
}

export type LeaderboardAction =
  | { type: "setEvaluateFor"; evaluateFor: EvaluateFor }
  | { type: "setPool"; pool: Pool }
  | { type: "setTop"; top: number }
  | { type: "setMinGames"; minGames: number };

export const PLAYER_ANALYSIS_KEY = "ffm.player-analysis.v1";
export const TOP_OPTIONS = [10, 15, 20, 25, 30, 35, 40, 45, 50];
export const MIN_GAMES_OPTIONS = Array.from({ length: 15 }, (_, i) => i + 1);

export const defaultLeaderboard: LeaderboardSettings = {
  evaluateFor: "team",
  pool: "free_agents",
  top: 25,
  minGames: 5,
};

export function leaderboardReducer(s: LeaderboardSettings, a: LeaderboardAction): LeaderboardSettings {
  switch (a.type) {
    case "setEvaluateFor":
      return { ...s, evaluateFor: a.evaluateFor };
    case "setPool":
      return { ...s, pool: a.pool };
    case "setTop":
      return { ...s, top: a.top };
    case "setMinGames":
      return { ...s, minGames: a.minGames };
  }
}

/** Stored values are kept only when valid; anything else falls back to its default. */
export function sanitize(raw: unknown): LeaderboardSettings {
  const r = (raw && typeof raw === "object" ? raw : {}) as Partial<Record<keyof LeaderboardSettings, unknown>>;
  const d = defaultLeaderboard;
  return {
    evaluateFor: r.evaluateFor === "team" || r.evaluateFor === "league" ? r.evaluateFor : d.evaluateFor,
    pool:
      r.pool === "free_agents" || r.pool === "all" || (Number.isInteger(r.pool) && (r.pool as number) > 0)
        ? (r.pool as Pool)
        : d.pool,
    top: TOP_OPTIONS.includes(r.top as number) ? (r.top as number) : d.top,
    minGames: MIN_GAMES_OPTIONS.includes(r.minGames as number) ? (r.minGames as number) : d.minGames,
  };
}

function load(): LeaderboardSettings {
  try {
    const raw = sessionStorage.getItem(PLAYER_ANALYSIS_KEY);
    return raw ? sanitize(JSON.parse(raw)) : defaultLeaderboard;
  } catch {
    return defaultLeaderboard; // storage unavailable or corrupt: start fresh
  }
}

export function usePlayerAnalysis() {
  const [state, dispatch] = useReducer(leaderboardReducer, undefined, load);
  useEffect(() => {
    try {
      sessionStorage.setItem(PLAYER_ANALYSIS_KEY, JSON.stringify(state));
    } catch {
      // storage unavailable: settings just won't survive a reload
    }
  }, [state]);
  return [state, dispatch] as const;
}
