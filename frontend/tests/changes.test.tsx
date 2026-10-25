import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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

type Any = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

function seed(teamId: number, mode = "strategic", opponentId: number | null = null) {
  sessionStorage.setItem(
    "ffm.impact.v3",
    JSON.stringify({ settings: { leagueId: 1, teamId, mode, opponentId }, moves: [] }),
  );
}

async function show(result: Any, teamId: number, mode = "strategic", opponentId: number | null = null) {
  analyze.mockImplementation(async () => result);
  seed(teamId, mode, opponentId);
  render(<App />);
  return (await screen.findByRole("heading", { level: 2 }, { timeout: 2000 })).closest("header")!;
}

const nonNull = (o: Any) => Object.values(o).filter(Boolean).length;

describe("change markers (003)", () => {
  beforeEach(() => sessionStorage.clear());
  afterEach(cleanup);

  it("shows nothing without moves", async () => {
    await show(strategic, 4);
    expect(document.querySelectorAll(".delta")).toHaveLength(0);
    expect(document.querySelector('[data-testid="radar-original"]')).toBeNull();
    expect(document.querySelector('[data-testid="radar-before"]')).toBeNull();
  });

  it("headline: W/L/T deltas with server tones (strategic)", async () => {
    const header = await show(strategicMoves, 4);
    const h = (strategicMoves as Any).changes.header;
    const line = header.querySelector(".score .delta-line")!;
    // Below the record: only the change in wins.
    expect(line).toHaveTextContent(`${h.wins.delta > 0 ? "+" : "−"}${Math.abs(h.wins.delta)}`);
    expect(line.querySelector(`.delta-${h.wins.tone}`)).not.toBeNull();
    expect(line.textContent).not.toContain("–");
  });

  it("headline: chance-to-win delta (tactical)", async () => {
    const header = await show(tacticalMoves, 3, "tactical", 4);
    const d = (tacticalMoves as Any).changes.header.chance_to_win;
    const line = header.querySelector(".score .delta-line")!;
    expect(line.querySelector(`.delta-${d.tone}`)).toHaveTextContent(`+${d.delta.toFixed(0)}%`);
    expect(within(header).getByLabelText("Chance to win")).not.toHaveTextContent("+");
    expect(within(header).getByLabelText("Chance to win").querySelector(`.wins-${d.tone}`)).not.toBeNull();
  });

  it("radar: dotted original outline, no red/green layers", async () => {
    await show(strategicMoves, 4);
    const orig = document.querySelectorAll('[data-testid="radar-original"]');
    expect(orig).toHaveLength(1);
    expect(orig[0]).toHaveAttribute("stroke-dasharray", "4,3");
    expect(document.querySelector('[data-testid="radar-before"]')).toBeNull();
    expect(document.querySelector('[data-testid="radar-after"]')).toBeNull();
  });

  it("radar tabs, ranking table, curves, and H2H show changes", async () => {
    await show(strategicMoves, 4);
    const ch = (strategicMoves as Any).changes;
    // tabs
    const tabDeltas = document.querySelectorAll(".radar-scale .delta");
    expect(tabDeltas).toHaveLength(nonNull(ch.radar.area));
    // ranking table
    const table = document.querySelector(".category-table") as HTMLElement;
    const expected = Object.values(ch.category_table).reduce((n: number, r) => n + nonNull(r as Any), 0);
    expect(table.querySelectorAll(".delta")).toHaveLength(expected);
    // curves: original layer drawn and legend entry
    // Legend: "<Team> (before)" right after the selected team's entry.
    const items = Array.from(document.querySelectorAll(".curve-legend .legend-item")).map((e) => e.textContent);
    const team = (strategicMoves as Any).header.team_name;
    expect(items.indexOf(`${team} (before)`)).toBe(items.indexOf(team) + 1);
    // H2H: flip styling and deltas
    const h2h = document.querySelector("table.record-table") as HTMLElement;
    const flips = Object.values(ch.matchups).filter((m) => (m as Any).transition === "flip_better").length;
    expect(h2h.querySelectorAll(".flip-better")).toHaveLength(flips);
    expect(h2h.querySelector(".flip-better")).toHaveAttribute("title", "was L");
    expect(h2h.querySelector("tfoot .delta")).not.toBeNull();
  });

  it("tactical difference table shows You/Opp/Diff/Win % deltas, Opp inverted by the server", async () => {
    await show(tacticalMoves, 3, "tactical", 4);
    const ch = (tacticalMoves as Any).changes.category_table;
    const table = document.querySelector(".category-table") as HTMLElement;
    const expected = Object.values(ch).reduce((n: number, r) => n + nonNull(r as Any), 0);
    expect(table.querySelectorAll(".delta")).toHaveLength(expected);
    expect(document.querySelectorAll('[data-testid="radar-original"]')).toHaveLength(1); // yours only, not the opponent's
  });

  it("roster is unchanged: no rows for dropped or traded players (option A)", async () => {
    await show(strategicMoves, 4);
    const roster = document.querySelector("table.roster") as HTMLElement;
    const team = (strategicMoves as Any).rosters.find((r: Any) => r.team_id === 4);
    expect(roster.querySelectorAll("tbody tr")).toHaveLength(team.players.length);
    expect(roster.querySelector(".removed")).toBeNull();
  });
});

describe("percentage changes", () => {
  afterEach(cleanup);
  it("show a % sign in Win % columns; counts and averages don't", async () => {
    analyze.mockImplementation(async () => strategicMoves);
    seed(4);
    render(<App />);
    await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
    const rows = Array.from(document.querySelectorAll(".category-table tbody tr"));
    for (const row of rows) {
      const cells = row.querySelectorAll("td");
      const winDelta = cells[5].querySelector(".delta");
      if (winDelta) expect(winDelta.textContent).toMatch(/%$/);
      const rankDelta = cells[1].querySelector(".delta");
      if (rankDelta) expect(rankDelta.textContent).not.toContain("%");
    }
    const h2hWin = document.querySelector("table.record-table tbody td:nth-child(3) .delta");
    if (h2hWin) expect(h2hWin.textContent).toMatch(/%$/);
  });
});

describe("changed W counts", () => {
  afterEach(cleanup);
  it("color the W number by its change in the headline and H2H", async () => {
    analyze.mockImplementation(async () => strategicMoves);
    seed(4);
    render(<App />);
    const header = (await screen.findByRole("heading", { level: 2 }, { timeout: 2000 })).closest("header")!;
    const wins = (strategicMoves as Any).changes.header.wins;
    expect(within(header).getByLabelText("Projected record").querySelector(`.wins-${wins.tone}`)).toHaveTextContent(
      String((strategicMoves as Any).header.record.wins),
    );
    const changedRows = Object.values((strategicMoves as Any).changes.matchups).filter(
      (m) => (m as Any).category_record.wins,
    ).length;
    const colored = document.querySelectorAll("table.record-table tbody .wins-better, table.record-table tbody .wins-worse");
    expect(colored).toHaveLength(changedRows);
  });
});
