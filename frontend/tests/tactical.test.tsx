import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import league from "./fixtures/league.json";
import leagues from "./fixtures/leagues.json";
import strategic from "./fixtures/strategic.json";
import tactical from "./fixtures/tactical.json";

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
type Req = { mode?: string; opponent_id?: number | null };

function seed(mode: string, opponentId: number | null) {
  sessionStorage.setItem(
    "ffm.impact.v1",
    JSON.stringify({ settings: { leagueId: 1, teamId: 3, mode, opponentId }, moves: [] }),
  );
}

describe("tactical mode (US3)", () => {
  beforeEach(() => {
    sessionStorage.clear();
    analyze.mockReset();
    analyze.mockImplementation(async (req: Req) =>
      req.mode === "tactical" && req.opponent_id ? tactical : strategic,
    );
  });
  afterEach(cleanup);

  it("shows opponent and week controls only in tactical mode", async () => {
    const user = userEvent.setup();
    seed("strategic", null);
    render(<App />);
    await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
    expect(screen.queryByLabelText("Opponent")).toBeNull();
    await user.click(screen.getByRole("radio", { name: "Tactical" }));
    expect(screen.getByLabelText("Opponent")).toBeInTheDocument();
    expect(screen.getByLabelText("Period start")).toBeInTheDocument();
  });

  it("shows the category record, win %, differences and games left", async () => {
    seed("tactical", 2);
    render(<App />);
    const header = (await screen.findByRole("heading", { level: 2 }, { timeout: 2000 })).closest("header")!;
    const pct = Math.round(tactical.header.matchup_win_probability! * 100);
    expect(within(header).getByLabelText("Chance to win")).toHaveTextContent(`${pct}%`);
    expect(within(header).getByText("Chance to Win")).toBeInTheDocument();
    expect(within(header).getByRole("heading", { level: 3 })).toHaveTextContent("vs. Betas");
    expect(within(header).queryByLabelText("Projected record")).toBeNull();
    expect(screen.getByText("Per Category Difference")).toBeInTheDocument();
    const firstRow = document.querySelector(".category-table tbody tr")!;
    const ptsWin = Math.round((tactical.category_table!.rows[0] as { win_probability: number }).win_probability * 100);
    expect(firstRow.querySelectorAll("td")[4]).toHaveTextContent(`${ptsWin}%`);
    const pts = document.querySelector('.category-table tbody tr td[data-favors]')!;
    expect(pts).toHaveAttribute("data-favors", tactical.category_table!.rows[0].favors as string);
    const roster = document.querySelector("table.roster")!;
    expect(within(roster as HTMLElement).getByTitle("Games left in the period")).toBeInTheDocument();
    expect(document.querySelectorAll('[data-testid="radar-other"]')).toHaveLength(0);
    expect(document.querySelectorAll('[data-testid="radar-opponent"]')).toHaveLength(1);
    const h2h = document.querySelector("table.record-table")!;
    expect(h2h.querySelectorAll("tbody tr")).toHaveLength(3); // league-wide, not filtered
    expect(h2h.querySelector("tr.opponent-row")).toHaveTextContent("Betas");
  });

  it("asks for an opponent when none is chosen", async () => {
    analyze.mockImplementation(async () => ({
      ...tactical,
      header: { ...tactical.header, record: null, matchup_win_probability: null },
      radar: null,
      category_table: null,
      curves: [],
      matchups: [],
      matchup_totals: null,
      warnings: [{ code: "OPPONENT_REQUIRED", message: "Choose an opponent to see this week's matchup." }],
    }));
    seed("tactical", null);
    render(<App />);
    expect(await screen.findByText("Choose an opponent", {}, { timeout: 2000 })).toBeInTheDocument();
  });
});
