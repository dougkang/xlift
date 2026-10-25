/** 003 FR-019: changes sit on a reserved line below their value, so the layout is the same
 * with and without moves. */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import league from "./fixtures/league.json";
import leagues from "./fixtures/leagues.json";
import strategic from "./fixtures/strategic.json";
import strategicMoves from "./fixtures/strategic_moves.json";
import tacticalMoves from "./fixtures/tactical_moves.json";

const analyze = vi.fn();
vi.mock("../src/api/client", async (orig) => {
  const actual = await orig<typeof import("../src/api/client")>();
  return {
    ...actual,
    listLeagues: vi.fn(async () => leagues),
    getLeague: vi.fn(async () => league),
    analyze: (...args: unknown[]) => analyze(...args),
    players: vi.fn(async () => ({ total: 0, players: [] })),
  };
});
const { default: App } = await import("../src/App");

async function renderWith(fixture: unknown, teamId: number, mode = "strategic", opp: number | null = null) {
  analyze.mockImplementation(async () => fixture);
  sessionStorage.setItem(
    "ffm.impact.v3",
    JSON.stringify({ settings: { leagueId: 1, teamId, mode, opponentId: opp }, moves: [] }),
  );
  render(<App />);
  await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
}

describe("layout stability", () => {
  afterEach(cleanup);

  it.each([
    ["strategic", strategicMoves, 4, null],
    ["tactical", tacticalMoves, 3, 4],
  ])("%s: every change sits on a reserved line below its value", async (mode, fixture, teamId, opp) => {
    await renderWith(fixture, teamId as number, mode as string, opp as number | null);
    const deltas = Array.from(document.querySelectorAll(".delta"));
    expect(deltas.length).toBeGreaterThan(0);
    for (const d of deltas) {
      expect(d.closest(".delta-line")).not.toBeNull();
    }
  });

  it("reserves the change lines even without moves, so nothing shifts when they appear", async () => {
    await renderWith(strategic, 4);
    expect(document.querySelectorAll(".delta")).toHaveLength(0);
    const lines = document.querySelectorAll(".delta-line");
    // headline + 3 radar tabs + 9 rows x 5 ranking cells + H2H (3 rows x 2 + 2 totals)
    expect(lines.length).toBe(1 + 3 + 9 * 5 + 3 * 2 + 2);
  });
});
