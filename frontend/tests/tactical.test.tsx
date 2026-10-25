/** Tactical = the current matchup (005): opponent and week come from the imported matchups.csv. */
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import league from "./fixtures/league.json";
import leagues from "./fixtures/leagues.json";
import strategic from "./fixtures/strategic.json";
import tactical from "./fixtures/tactical.json";

const analyze = vi.fn();
let leagueFixture: unknown = league;
vi.mock("../src/api/client", async (orig) => {
  const actual = await orig<typeof import("../src/api/client")>();
  return {
    ...actual,
    listLeagues: vi.fn(async () => leagues),
    getLeague: vi.fn(async () => leagueFixture),
    analyze: (...args: unknown[]) => analyze(...args),
    players: vi.fn(async () => ({ total: 0, players: [] })),
  };
});

const { default: App } = await import("../src/App");
type Req = { mode?: string };
const matchup = tactical.header.matchup!;

function seed(mode: string, extra: Record<string, unknown> = {}) {
  sessionStorage.setItem(
    "ffm.impact.v2",
    JSON.stringify({ settings: { leagueId: 1, teamId: 3, mode, ...extra }, moves: [] }),
  );
}

async function renderTactical() {
  seed("tactical");
  render(<App />);
  return (await screen.findByRole("heading", { level: 2 }, { timeout: 2000 })).closest("header")!;
}

describe("tactical mode: the current matchup (005)", () => {
  beforeEach(() => {
    sessionStorage.clear();
    leagueFixture = league;
    analyze.mockReset();
    analyze.mockImplementation(async (req: Req) => (req.mode === "tactical" ? tactical : strategic));
  });
  afterEach(cleanup);

  it("has no opponent or week controls, and sends neither", async () => {
    const user = userEvent.setup();
    seed("strategic");
    render(<App />);
    await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
    await user.click(screen.getByRole("radio", { name: "Tactical" }));
    expect(screen.queryByLabelText("Opponent")).toBeNull();
    expect(screen.queryByLabelText("Period start")).toBeNull();
    await screen.findByText("Per Category Difference", {}, { timeout: 2000 });
    const req = analyze.mock.calls.at(-1)![0] as Record<string, unknown>;
    expect(req.mode).toBe("tactical");
    expect(req).not.toHaveProperty("opponent_id");
    expect(req).not.toHaveProperty("period_start");
  });

  it("ignores an opponent and week saved by an older session", async () => {
    seed("tactical", { opponentId: 2, periodStart: "2026-11-01", periodEnd: "2026-11-07" });
    render(<App />);
    await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
    const saved = JSON.parse(sessionStorage.getItem("ffm.impact.v2")!).settings;
    expect(saved).not.toHaveProperty("opponentId");
    expect(saved).not.toHaveProperty("periodStart");
  });

  it("disables Tactical when no matchup is imported", async () => {
    leagueFixture = { ...league, current_matchup: null };
    seed("tactical");
    render(<App />);
    await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
    const toggle = screen.getByRole("radio", { name: "Tactical" });
    expect(toggle).toBeDisabled();
    expect(toggle).toHaveAttribute("title", "This week's matchup hasn't been loaded yet");
    expect(screen.getByRole("radio", { name: "Strategic" })).toHaveAttribute("aria-checked", "true");
  });

  it("shows the opponent, the score so far, and Chance to Win", async () => {
    const header = await renderTactical();
    const pct = Math.round(tactical.header.matchup_win_probability! * 100);
    expect(within(header).getByLabelText("Chance to win")).toHaveTextContent(`${pct}%`);
    expect(within(header).getByRole("heading", { level: 3 })).toHaveTextContent(`vs. ${matchup.opponent_name}`);
    const { wins, losses, ties } = matchup.current;
    expect(within(header).getByLabelText("Current matchup score")).toHaveTextContent(
      `Week 1 · Nov 16–Nov 22 · Now ${wins}–${losses}–${ties}`,
    );
    // The line sits above the team name; the as-of date is with the other "last updated" dates.
    const line = within(header).getByLabelText("Current matchup score");
    expect(line.compareDocumentPosition(within(header).getByRole("heading", { level: 2 }))).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
    expect(screen.getByText(`Matchup last updated: ${matchup.as_of}`)).toBeInTheDocument();
  });

  it("marks a finished week as final", async () => {
    analyze.mockImplementation(async () => ({
      ...tactical,
      header: { ...tactical.header, matchup: { ...matchup, final: true } },
    }));
    const header = await renderTactical();
    const line = within(header).getByLabelText("Current matchup score");
    expect(line).toHaveTextContent(`Final ${matchup.current.wins}–`);
  });

  it("shows week-to-date values next to the projected finals", async () => {
    await renderTactical();
    expect(screen.getByText("Per Category Difference")).toBeInTheDocument();
    const row = tactical.category_table!.rows[0] as { selected_actual: number; opponent_actual: number };
    const first = document.querySelector(".category-table tbody tr")!;
    const cells = first.querySelectorAll("td");
    expect(cells[1]).toHaveClass("now-col");
    expect(cells[1]).toHaveTextContent(`${row.selected_actual}–${row.opponent_actual}`);
    const ptsWin = Math.round((tactical.category_table!.rows[0] as { win_probability: number }).win_probability * 100);
    expect(cells[5]).toHaveTextContent(`${ptsWin}%`);
  });

  it("replaces H2H with the opponent's read-only roster", async () => {
    await renderTactical();
    expect(document.querySelector("table.record-table")).toBeNull();
    const title = screen.getByRole("heading", { level: 3, name: new RegExp(`^${matchup.opponent_name}`) });
    const section = title.closest("section")!;
    const opp = tactical.rosters.find((r) => r.team_id === matchup.opponent_id)!;
    for (const p of opp.players) expect(within(section).getByText(p.name)).toBeInTheDocument();
    expect(within(section).queryAllByRole("button", { name: /^Drop / })).toHaveLength(0);
    expect(within(section).getByTitle("Games left in the period")).toBeInTheDocument();
    // Each roster carries only its own players' footnotes.
    const oppIds = new Set(opp.players.map((p) => p.player_id));
    const notes = section.querySelectorAll(".footnotes li");
    expect(notes).toHaveLength(tactical.footnotes.filter((f) => oppIds.has(f.player_id)).length);
    expect(notes.length).toBeGreaterThan(0);
    // Your own roster still has its drop buttons.
    expect(screen.getAllByRole("button", { name: /^Drop / }).length).toBeGreaterThan(0);
  });

  it("shows the server's notice when no matchup is loaded", async () => {
    analyze.mockImplementation(async () => ({
      ...tactical,
      header: { ...tactical.header, record: null, matchup_win_probability: null, matchup: null },
      radar: null,
      category_table: null,
      curves: [],
      warnings: [
        { code: "MATCHUP_NOT_LOADED", message: "This week's matchup hasn't been loaded yet." },
      ],
    }));
    seed("tactical");
    render(<App />);
    expect(await screen.findByText(/matchup hasn't been loaded yet/, {}, { timeout: 2000 })).toBeInTheDocument();
  });
});
