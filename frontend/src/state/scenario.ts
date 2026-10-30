import { useEffect, useReducer } from "react";
import type { Move } from "../api/client";

export type Mode = "strategic" | "tactical";
export type RadarScale = "rank" | "average" | "winrate";
/** Fragility Penalty (007): how availability is estimated for the whole analysis. */
export type Fragility = "none" | "last15" | "dab" | "dab_tag";

export interface Settings {
  leagueId: number | null;
  teamId: number | null;
  mode: Mode;
  window: number;
  fragility: Fragility;
  /** Radar scale: category rank, or each category's average min-max scaled across the league. */
  radarScale: RadarScale;
}

export interface ScenarioState {
  settings: Settings;
  moves: Move[];
  /** The H2H opponent the page compares with instead of the league (011, strategic). Not saved:
   * a reload starts from the league view. */
  focusOpponentId: number | null;
}

export type Action =
  | { type: "setLeague"; leagueId: number }
  | { type: "setTeam"; teamId: number }
  | { type: "setMode"; mode: Mode }
  | { type: "setWindow"; window: number }
  | { type: "setFragility"; fragility: Fragility }
  | { type: "setRadarScale"; scale: RadarScale }
  | { type: "addMove"; move: Move }
  | { type: "popMove" }
  | { type: "reset" }
  /** Clicking an H2H row: focuses that opponent, or clears focus if it's already focused. */
  | { type: "toggleFocus"; opponentId: number };

// v2: 006 changed the default window to 82; v3: 007 added the Fragility Penalty. Sessions saved
// under an older key start fresh.
export const STORAGE_KEY = "ffm.impact.v3";

export const initialState: ScenarioState = {
  settings: {
    leagueId: null,
    teamId: null,
    mode: "strategic",
    window: 82,
    fragility: "dab_tag",
    radarScale: "winrate",
  },
  moves: [],
  focusOpponentId: null,
};

export function reducer(state: ScenarioState, action: Action): ScenarioState {
  const s = state.settings;
  switch (action.type) {
    case "setLeague":
      return { settings: { ...s, leagueId: action.leagueId, teamId: null }, moves: [], focusOpponentId: null };
    // A new team or mode starts from the league view (011 FR-004).
    case "setTeam":
      return { ...state, settings: { ...s, teamId: action.teamId }, focusOpponentId: null };
    case "setMode":
      return { ...state, settings: { ...s, mode: action.mode }, focusOpponentId: null };
    case "setWindow":
      return { ...state, settings: { ...s, window: action.window } };
    case "setFragility":
      return { ...state, settings: { ...s, fragility: action.fragility } };
    case "setRadarScale":
      return { ...state, settings: { ...s, radarScale: action.scale } };
    case "addMove":
      return { ...state, moves: [...state.moves, action.move] };
    case "popMove":
      return { ...state, moves: state.moves.slice(0, -1) };
    case "reset":
      return { ...state, moves: [] };
    case "toggleFocus":
      return {
        ...state,
        focusOpponentId: state.focusOpponentId === action.opponentId ? null : action.opponentId,
      };
  }
}

function load(): ScenarioState {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as ScenarioState;
      // Keep only known settings: sessions saved before 005 may still carry an opponent or week.
      const settings = { ...initialState.settings };
      for (const k of Object.keys(settings) as (keyof Settings)[]) {
        if (parsed.settings && k in parsed.settings) (settings as Record<string, unknown>)[k] = parsed.settings[k];
      }
      return { settings, moves: parsed.moves ?? [], focusOpponentId: null };
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
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ settings: state.settings, moves: state.moves }));
    } catch {
      // storage unavailable: moves just won't survive a reload
    }
  }, [state]);
  return [state, dispatch] as const;
}
