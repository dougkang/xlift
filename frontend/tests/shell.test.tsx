import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import board from "./fixtures/leaderboard.json";
import league from "./fixtures/league.json";
import leagues from "./fixtures/leagues.json";
import strategic from "./fixtures/strategic.json";
import tactical from "./fixtures/tactical.json";

const leaderboardMock = vi.fn(async (..._args: unknown[]) => structuredClone(board));
const analyzeMock = vi.fn(async (req: { mode?: string }) => (req.mode === "tactical" ? tactical : strategic));
vi.mock("../src/api/client", async (orig) => {
  const actual = await orig<typeof import("../src/api/client")>();
  return {
    ...actual,
    listLeagues: vi.fn(async () => leagues),
    getLeague: vi.fn(async () => ({ ...league, current_matchup: tactical.header.matchup ?? null })),
    analyze: (req: { mode?: string }) => analyzeMock(req),
    players: vi.fn(async () => ({ total: 0, players: [] })),
    leaderboard: (...args: unknown[]) => leaderboardMock(...args),
  };
});

const { Shell } = await import("../src/Shell");

afterEach(cleanup);

async function go(hash: string) {
  await act(async () => {
    window.location.hash = hash;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}

const nav = () => screen.getByRole("navigation", { name: "Tools" });
const lastBoard = () => leaderboardMock.mock.calls.at(-1)![0] as Record<string, unknown>;

describe("the tool shell", () => {
  beforeEach(async () => {
    sessionStorage.clear();
    leaderboardMock.mockClear();
    analyzeMock.mockClear();
    window.location.hash = "#/";
  });

  it("shows the nav on both tools and marks the current one", async () => {
    sessionStorage.setItem("ffm.impact.v3", JSON.stringify({ settings: { leagueId: 1, teamId: 4 }, moves: [] }));
    render(<Shell />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Impact Analysis");
    expect(within(nav()).getByRole("link", { name: "Impact Analysis" })).toHaveAttribute("aria-current", "page");
    expect(within(nav()).getByRole("link", { name: "Player Analysis" })).toHaveAttribute("href", "#/player-analysis");
    expect(within(nav()).getByRole("link", { name: "How it works" })).toHaveAttribute("href", "./how-it-works.html");
    await go("#/player-analysis");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Player Analysis");
    expect(within(nav()).getByRole("link", { name: "Player Analysis" })).toHaveAttribute("aria-current", "page");
    expect(within(nav()).getByRole("link", { name: "Impact Analysis" })).not.toHaveAttribute("aria-current");
    expect(document.title).toBe("Player Analysis");
  });

  it("carries league, team, window and Fragility Penalty to Player Analysis", async () => {
    sessionStorage.setItem("ffm.impact.v3", JSON.stringify({ settings: { leagueId: 1, teamId: 4 }, moves: [] }));
    render(<Shell />);
    await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
    fireEvent.change(screen.getByRole("combobox", { name: /Fragility Penalty/ }), { target: { value: "none" } });
    fireEvent.change(screen.getByLabelText("Games in window"), { target: { value: "40" } });
    fireEvent.change(screen.getByRole("combobox", { name: /Team/ }), { target: { value: "2" } });
    await go("#/player-analysis");
    await screen.findAllByTestId("leaderboard-row", undefined, { timeout: 2000 });
    expect(lastBoard()).toMatchObject({ league_id: 1, team_id: 2, window: 40, fragility: "none" });
  });

  it("keeps Impact Analysis's moves and mode, and says the leaderboard ignores the moves", async () => {
    const move = { type: "drop", player_id: 10, team_id: 4 };
    sessionStorage.setItem(
      "ffm.impact.v3",
      JSON.stringify({ settings: { leagueId: 1, teamId: 4, mode: "tactical" }, moves: [move] }),
    );
    window.location.hash = "#/player-analysis";
    render(<Shell />);
    await screen.findAllByTestId("leaderboard-row", undefined, { timeout: 2000 });
    expect(
      screen.getByText("The leaderboard uses rosters as they are, without your Impact Analysis moves."),
    ).toBeInTheDocument();
    expect(lastBoard()).not.toHaveProperty("moves");
    expect(lastBoard()).not.toHaveProperty("mode");
    await go("#/");
    const stored = JSON.parse(sessionStorage.getItem("ffm.impact.v3")!);
    expect(stored.moves).toEqual([move]);
    expect(stored.settings.mode).toBe("tactical");
    expect(screen.getByRole("radio", { name: "Tactical" })).toHaveAttribute("aria-checked", "true");
  });

  it("shows no moves note without moves", async () => {
    sessionStorage.setItem("ffm.impact.v3", JSON.stringify({ settings: { leagueId: 1, teamId: 4 }, moves: [] }));
    window.location.hash = "#/player-analysis";
    render(<Shell />);
    await screen.findAllByTestId("leaderboard-row", undefined, { timeout: 2000 });
    expect(screen.queryByText(/without your Impact Analysis moves/)).toBeNull();
  });
});
