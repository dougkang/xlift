/** The Trade Finder (014). */
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import board from "./fixtures/leaderboard.json";
import league from "./fixtures/league.json";
import leagues from "./fixtures/leagues.json";

const player = (player_id: number, name: string, status = "healthy") => ({ player_id, name, nba_team: "MIA", status });
const result = {
  settings: { mode: "strategic", window: 82, as_of: "2026-11-18", fragility: "dab_tag" },
  team_id: 4,
  team_name: "Deltas",
  categories: [
    { key: "reb", label: "REB", higher_is_better: true },
    { key: "fg3m", label: "3PM", higher_is_better: true },
  ],
  rows: [
    {
      team_id: 2,
      team_name: "Betas",
      manager: "Bea",
      trade: {
        give: player(41, "Delta One"),
        get: player(21, "Beta One", "Q"),
        your_gain: 0.42,
        their_gain: 0.31,
        your_categories: [
          { category: "reb", gain: 1.2 },
          { category: "fg3m", gain: -0.6 },
        ],
      },
    },
    { team_id: 1, team_name: "Alphas", manager: "Ann", trade: null },
  ],
  warnings: [],
};

const tradesMock = vi.fn(async (..._args: unknown[]) => structuredClone(result));
vi.mock("../src/api/client", async (orig) => {
  const actual = await orig<typeof import("../src/api/client")>();
  return {
    ...actual,
    listLeagues: vi.fn(async () => leagues),
    getLeague: vi.fn(async () => league),
    leaderboard: vi.fn(async () => structuredClone(board)),
    trades: (...args: unknown[]) => tradesMock(...args),
    analyze: vi.fn(() => new Promise(() => {})),
    players: vi.fn(async () => ({ total: 0, players: [] })),
  };
});
const { Shell } = await import("../src/Shell");

function renderPage(moves: unknown[] = []) {
  sessionStorage.setItem("ffm.impact.v3", JSON.stringify({ settings: { leagueId: 1, teamId: 4 }, moves }));
  window.location.hash = "#/player-analysis";
  return render(<Shell />);
}

describe("trade finder (014)", () => {
  afterEach(cleanup);

  it("asks for the selected team's trades with the shared settings", async () => {
    renderPage();
    await waitFor(() => expect(tradesMock).toHaveBeenCalled(), { timeout: 2000 });
    expect(tradesMock.mock.calls.at(-1)![0]).toMatchObject({ league_id: 1, team_id: 4, window: 82, fragility: "dab_tag" });
  });

  it("draws one row per team: the trade, both gains, why; or no trade", async () => {
    renderPage();
    const rows = await screen.findAllByTestId("trade-row", undefined, { timeout: 2000 });
    expect(rows).toHaveLength(2);
    const [betas, alphas] = rows;
    expect(betas).toHaveTextContent("Betas");
    expect(betas).toHaveTextContent("Delta One");
    expect(betas).toHaveTextContent("Beta One");
    expect(betas).toHaveTextContent("+0.42");
    expect(betas).toHaveTextContent("+0.31");
    // One column per category: your gain, bold when positive.
    const heads = [...document.querySelectorAll(".trades-table thead th")].map((th) => th.textContent);
    expect(heads).toEqual(["Team", "You give", "You get", "You", "Them", "REB", "3PM", ""]);
    const [reb, threes] = betas.querySelectorAll("td.cat-col");
    expect(reb).toHaveTextContent("+1.2");
    expect(reb).toHaveClass("gain");
    expect(threes).toHaveTextContent("−0.6");
    expect(threes).not.toHaveClass("gain");
    expect(within(betas).getByText("Q")).toHaveClass("status");
    expect(alphas).toHaveTextContent("No trade helps both teams.");
  });

  it("Try it opens Impact Analysis with just that swap", async () => {
    renderPage([{ type: "drop", player_id: 7, team_id: 4 }]);
    const button = await screen.findByRole("button", { name: "Try it (replaces your moves)" }, { timeout: 2000 });
    fireEvent.click(button);
    await waitFor(() => expect(window.location.hash).toBe("#/"));
    const saved = JSON.parse(sessionStorage.getItem("ffm.impact.v3")!);
    expect(saved.moves).toEqual([{ type: "swap", acquire_id: 21, give_id: 41, team_id: 4 }]);
  });
});
