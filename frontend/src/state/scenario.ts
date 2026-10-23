import { useEffect, useReducer } from "react";
import type { Move } from "../api/client";

export type Mode = "strategic" | "tactical";

export interface Settings {
  leagueId: number | null;
  teamId: number | null;
  mode: Mode;
  window: number;
  opponentId: number | null;
  periodStart: string | null;
  periodEnd: string | null;
}

export interface ScenarioState {
  settings: Settings;
  moves: Move[];
}

export type Action =
  | { type: "setLeague"; leagueId: number }
  | { type: "setTeam"; teamId: number }
  | { type: "setMode"; mode: Mode }
  | { type: "setWindow"; window: number }
  | { type: "setOpponent"; opponentId: number | null }
  | { type: "setPeriod"; start: string | null; end: string | null }
  | { type: "addMove"; move: Move }
  | { type: "popMove" }
  | { type: "reset" };

export const STORAGE_KEY = "ffm.impact.v1";

export const initialState: ScenarioState = {
  settings: {
    leagueId: null,
    teamId: null,
    mode: "strategic",
    window: 15,
    opponentId: null,
    periodStart: null,
    periodEnd: null,
  },
  moves: [],
};

export function reducer(state: ScenarioState, action: Action): ScenarioState {
  const s = state.settings;
  switch (action.type) {
    case "setLeague":
      return { settings: { ...s, leagueId: action.leagueId, teamId: null, opponentId: null }, moves: [] };
    case "setTeam":
      return { ...state, settings: { ...s, teamId: action.teamId, opponentId: s.opponentId === action.teamId ? null : s.opponentId } };
    case "setMode":
      return { ...state, settings: { ...s, mode: action.mode } };
    case "setWindow":
      return { ...state, settings: { ...s, window: action.window } };
    case "setOpponent":
      return { ...state, settings: { ...s, opponentId: action.opponentId } };
    case "setPeriod":
      return { ...state, settings: { ...s, periodStart: action.start, periodEnd: action.end } };
    case "addMove":
      return { ...state, moves: [...state.moves, action.move] };
    case "popMove":
      return { ...state, moves: state.moves.slice(0, -1) };
    case "reset":
      return { ...state, moves: [] };
  }
}

function load(): ScenarioState {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as ScenarioState;
      return { settings: { ...initialState.settings, ...parsed.settings }, moves: parsed.moves ?? [] };
    }
  } catch {
    // storage unavailable or corrupt: start fresh
  }
  return initialState;
}

export function useScenario() {
  const [state, dispatch] = useReducer(reducer, undefined, load);
  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // storage unavailable: moves just won't survive a reload
    }
  }, [state]);
  return [state, dispatch] as const;
}
