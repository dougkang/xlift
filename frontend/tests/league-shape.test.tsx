/** League shape and Against null in the strategic Category Breakdown (008). */
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HELP, type HelpContext } from "../src/help/content";
import league from "./fixtures/league.json";
import leagues from "./fixtures/leagues.json";
import strategic from "./fixtures/strategic.json";
import strategicMoves from "./fixtures/strategic_moves.json";
import tactical from "./fixtures/tactical.json";

let fixture: unknown = strategic;
vi.mock("../src/api/client", async (orig) => {
  const actual = await orig<typeof import("../src/api/client")>();
  return {
    ...actual,
    listLeagues: vi.fn(async () => leagues),
    getLeague: vi.fn(async () => league),
    analyze: vi.fn(async () => fixture),
    players: vi.fn(async () => ({ total: 0, players: [] })),
  };
});

const { default: App } = await import("../src/App");

type Shape = (typeof strategic.league_shape)[number];

async function renderWith(result: unknown, mode = "strategic") {
  fixture = result;
  sessionStorage.setItem(
    "ffm.impact.v3",
    JSON.stringify({ settings: { leagueId: 1, teamId: 4, mode }, moves: [] }),
  );
  render(<App />);
  await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
}

describe("league shape charts (008)", () => {
  beforeEach(() => sessionStorage.clear());
  afterEach(cleanup);

  it("shows League shape per category with the selected team marked", async () => {
    await renderWith(strategic);
    const charts = screen.getAllByTestId("league-shape");
    expect(charts).toHaveLength(strategic.league_shape.length);
    charts.forEach((svg, i) => {
      const shape = strategic.league_shape[i] as Shape;
      expect(svg.querySelectorAll("circle[data-team]")).toHaveLength(shape.teams.length);
      const mine = svg.querySelectorAll('circle[data-selected="true"]');
      expect(mine).toHaveLength(1);
      const me = shape.teams.find((t) => t.selected)!;
      expect(mine[0].querySelector("title")?.textContent).toContain(`${me.team_name} · rank ${me.rank}`);
    });
  });

  it("shows Against null with the climb and cushion marked", async () => {
    await renderWith(strategic);
    const charts = screen.getAllByTestId("against-null");
    const withGaps = strategic.league_shape.filter((s) => s.gaps.length);
    expect(charts).toHaveLength(withGaps.length);
    charts.forEach((svg, i) => {
      const shape = withGaps[i] as Shape;
      expect(svg.querySelectorAll("rect")).toHaveLength(shape.gaps.length);
      expect(svg.querySelector('[data-testid="null-line"]')).not.toBeNull();
      for (const mark of ["climb", "cushion"]) {
        const want = shape.gaps.filter((g) => g.mark === mark).length;
        expect(svg.querySelectorAll(`rect[data-mark="${mark}"]`)).toHaveLength(want);
        expect(want).toBeLessThanOrEqual(1);
      }
    });
  });

  it("omits Against null when a category has no gaps", async () => {
    const patched = structuredClone(strategic);
    patched.league_shape[0].gaps = [];
    await renderWith(patched);
    expect(screen.getAllByTestId("league-shape")).toHaveLength(patched.league_shape.length);
    expect(screen.getAllByTestId("against-null")).toHaveLength(patched.league_shape.length - 1);
  });

  it("shows nothing new in tactical mode", async () => {
    await renderWith(tactical, "tactical");
    expect(screen.queryAllByTestId("league-shape")).toHaveLength(0);
    expect(screen.queryAllByTestId("against-null")).toHaveLength(0);
  });

  it("marks the pre-move position only with moves", async () => {
    await renderWith(strategic);
    expect(screen.queryAllByTestId("shape-before")).toHaveLength(0);
    cleanup();
    await renderWith(strategicMoves);
    const before = screen.getAllByTestId("shape-before");
    expect(before).toHaveLength(strategicMoves.league_shape.filter((s) => s.before).length);
    expect(before[0].querySelector("title")?.textContent).toMatch(/^before your moves · rank \d+/);
  });

  it("explains both charts in strategic help only", () => {
    const ctx = (mode: HelpContext["mode"]): HelpContext => ({
      mode,
      iterations: 25000,
      window: 82,
      capacity: 10,
      opponentName: "Gammas",
      asOf: "2026-11-18",
    });
    const text = (mode: HelpContext["mode"]) => HELP.breakdown(ctx(mode)).reading.join(" ");
    expect(text("strategic")).toMatch(/projected value by place/);
    expect(text("strategic")).toMatch(/gap to reach each place/);
    expect(text("tactical")).not.toMatch(/by place|gap to reach/);
  });
});
