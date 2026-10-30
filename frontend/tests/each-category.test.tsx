/** H2H each-category standings (010): the expected category record in the headline, the H2H
 * table and the help. */
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import league from "./fixtures/league.json";
import leagues from "./fixtures/leagues.json";
import strategicEach from "./fixtures/strategic_each.json";
import strategicEachMoves from "./fixtures/strategic_each_moves.json";
import tacticalEach from "./fixtures/tactical_each.json";
import { HELP, helpText, type HelpContext } from "../src/help/content";

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

async function show(result: Any) {
  const s = result.settings;
  sessionStorage.setItem(
    "ffm.impact.v3",
    JSON.stringify({
      settings: { leagueId: 1, teamId: result.header.team_id, mode: s.mode, opponentId: s.opponent_id },
      moves: [],
    }),
  );
  analyze.mockImplementation(async () => result);
  render(<App />);
  return (await screen.findByRole("heading", { level: 2 }, { timeout: 2000 })).closest("header")!;
}

const rec = (r: Any) => [r.wins, r.losses, r.ties].map((v: number) => v.toFixed(1)).join("–");
const pct = (p: number) => `${Math.round(p * 100)}%`;

describe("each-category standings (010)", () => {
  beforeEach(() => sessionStorage.clear());
  afterEach(cleanup);

  it("strategic headline is the expected category record with its win %", async () => {
    const header = await show(strategicEach);
    const e = strategicEach.header.expected_record!;
    expect(within(header).getByText(/Aggregated Record/)).toBeInTheDocument();
    expect(within(header).getByLabelText("Projected record")).toHaveTextContent(rec(e));
    expect(within(header).getByLabelText("Standings win %")).toHaveTextContent(pct(e.win_pct));
    // The combined H2H score: the Total row of the H2H table.
    expect(within(header).getByLabelText("Projected record")).toHaveTextContent(
      rec(strategicEach.matchup_totals!.expected!),
    );
  });

  it("H2H shows Record and Win % per opponent, no Result column, Total = headline", async () => {
    await show(strategicEach);
    const table = document.querySelector("table.record-table") as HTMLElement;
    const heads = [...table.querySelectorAll("thead th")].map((th) => th.textContent);
    expect(heads).toEqual(["Opponent", "Record", "Win %"]);
    const rows = table.querySelectorAll("tbody tr");
    expect(rows).toHaveLength(strategicEach.matchups.length);
    const first = strategicEach.matchups[0].expected_record!;
    expect(rows[0]).toHaveTextContent(rec(first));
    expect(rows[0]).toHaveTextContent(pct(first.win_pct));
    const total = table.querySelector("tfoot tr")!;
    expect(total).toHaveTextContent(rec(strategicEach.header.expected_record!));
  });

  it("a move shows its change in expected wins, with no flip markers", async () => {
    const header = await show(strategicEachMoves);
    const ch = strategicEachMoves.changes!.header;
    expect(within(header).getByLabelText(`up ${ch.expected_wins!.delta.toFixed(1)}, better`)).toBeInTheDocument();
    expect(within(header).getByLabelText(`up ${ch.win_pct!.delta}%, better`)).toBeInTheDocument();
    const table = document.querySelector("table.record-table") as HTMLElement;
    expect(table.querySelector(".flip-better, .flip-worse")).toBeNull();
  });

  it("tactical headline is this week's projected record", async () => {
    const header = await show(tacticalEach);
    expect(within(header).getByText(/Projected Record/)).toBeInTheDocument();
    expect(within(header).getByLabelText("Projected record")).toHaveTextContent(
      rec(tacticalEach.header.expected_record!),
    );
    expect(within(header).queryByText(/Chance to Win/)).toBeNull();
  });

  it("help explains each-category scoring", () => {
    const ctx = (mode: HelpContext["mode"]): HelpContext => ({
      mode,
      iterations: 25000,
      window: 15,
      capacity: 13,
      opponentName: "Gammas",
      asOf: "2026-11-18",
      standings: "category",
    });
    const strategic = helpText(HELP.headline(ctx("strategic")));
    expect(strategic).toMatch(/every category of a matchup is a W, L or T/);
    expect(strategic).toMatch(/a tie counts half/);
    expect(helpText(HELP.headline(ctx("tactical")))).toMatch(/Projected Record/);
    expect(helpText(HELP.h2h(ctx("strategic")))).toMatch(/Win %: \(W \+ ½T\)/);
  });
});
