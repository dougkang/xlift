import type { components } from "./schema";

export type Schemas = components["schemas"];
type Defaulted = "mode" | "window" | "iterations" | "seed";
/** Fields with server-side defaults are optional to send. */
export type ScenarioRequest = Omit<Schemas["ScenarioRequest"], Defaulted> &
  Partial<Pick<Schemas["ScenarioRequest"], Defaulted>>;
export type AnalysisResult = Schemas["AnalysisResult"];
export type LeagueSummary = Schemas["LeagueSummary"];
export type LeagueDetail = Schemas["LeagueDetail"];
export type Move = ScenarioRequest["moves"] extends (infer M)[] | undefined ? M : never;

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    super(typeof detail === "object" && detail && "message" in detail
      ? String((detail as { message: unknown }).message)
      : `Request failed (${status})`);
  }

  get moveIndex(): number | null {
    const d = this.detail as { move_index?: number } | null;
    return d && typeof d.move_index === "number" ? d.move_index : null;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body?.detail ?? body);
  return body as T;
}

export const listLeagues = () => request<LeagueSummary[]>("/api/leagues");

export const getLeague = (leagueId: number) => request<LeagueDetail>(`/api/leagues/${leagueId}`);

export const analyze = (req: ScenarioRequest, signal?: AbortSignal) =>
  request<AnalysisResult>("/api/impact/analyze", {
    method: "POST",
    body: JSON.stringify(req),
    signal,
  });

export type PlayersRequest = ScenarioRequest & {
  query?: string;
  limit?: number;
  offset?: number;
  free_agents_only?: boolean;
};
export type PlayerPage = Schemas["PlayerPage"];
export type PlayerRow = Schemas["PlayerRow"];

export const players = (req: PlayersRequest, signal?: AbortSignal) =>
  request<PlayerPage>("/api/impact/players", {
    method: "POST",
    body: JSON.stringify(req),
    signal,
  });

/** Player Analysis (009): the xLift leaderboard. The league as imported: no moves, strategic. */
type LeaderboardDefaulted = "window" | "fragility" | "evaluate_for" | "pool" | "top" | "min_games";
export type LeaderboardRequest = Omit<Schemas["LeaderboardRequest"], LeaderboardDefaulted> &
  Partial<Pick<Schemas["LeaderboardRequest"], LeaderboardDefaulted>>;
export type Leaderboard = Schemas["Leaderboard"];
export type LeaderboardEntry = Schemas["LeaderboardEntry"];
export type LeaderboardCategory = Schemas["LeaderboardCategory"];

export const leaderboard = (req: LeaderboardRequest, signal?: AbortSignal) =>
  request<Leaderboard>("/api/player-analysis/leaderboard", {
    method: "POST",
    body: JSON.stringify(req),
    signal,
  });
