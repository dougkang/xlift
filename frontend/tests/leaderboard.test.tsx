import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import board from "./fixtures/leaderboard.json";
import league from "./fixtures/league.json";
import leagues from "./fixtures/leagues.json";

const leaderboardMock = vi.fn(async (..._args: unknown[]) => structuredClone(board));
vi.mock("../src/api/client", async (orig) => {
  const actual = await orig<typeof import("../src/api/client")>();
  return {
    ...actual,
    listLeagues: vi.fn(async () => leagues),
    getLeague: vi.fn(async () => league),
    leaderboard: (...args: unknown[]) => leaderboardMock(...args),
  };
});

const { Leaderboard, CATEGORY_COLORS } = await import("../src/player-analysis/Leaderboard");
const { Shell } = await import("../src/Shell");

afterEach(cleanup);

const lastRequest = () => leaderboardMock.mock.calls.at(-1)![0] as Record<string, unknown>;

function renderPage(moves: unknown[] = []) {
  sessionStorage.setItem("ffm.impact.v3", JSON.stringify({ settings: { leagueId: 1, teamId: 4 }, moves }));
  window.location.hash = "#/player-analysis";
  return render(<Shell />);
}

/** A segment's [left, right] in pixels, from Plot's rect. */
function extent(rect: Element): [number, number] {
  const x = Number(rect.getAttribute("x"));
  return [x, x + Number(rect.getAttribute("width"))];
}

function segment(player: string, category: string): Element {
  const rects = [...document.querySelectorAll('[data-testid="leaderboard-bars"] rect')];
  const r = rects.find((el) => el.querySelector("title")?.textContent?.startsWith(`${player} · ${category} · `));
  if (!r) throw new Error(`no segment ${player} ${category}`);
  return r;
}

function zeroX(): number {
  const lines = [...document.querySelectorAll('[data-testid="leaderboard-bars"] line')];
  const rule = lines.find((l) => l.getAttribute("stroke") === "#ccc" || l.closest('[stroke="#ccc"]'));
  return Number(rule!.getAttribute("x1") ?? rule!.getAttribute("x"));
}

describe("the leaderboard chart", () => {
  it("draws rows in the server's order with name, owner, status and signed net", () => {
    render(<Leaderboard categories={board.categories} entries={board.entries} />);
    const rows = screen.getAllByTestId("leaderboard-row");
    expect(rows.map((r) => within(r).getByText(/Streamer|Ray|Ben/).textContent)).toEqual([
      "Steady Streamer",
      "Rookie Ray",
      "Bench Ben",
    ]);
    expect(within(rows[0]).getByText("+1.80")).toBeInTheDocument();
    expect(within(rows[2]).getByText("−0.23")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Q")).toHaveClass("status");
    expect(within(rows[1]).getByText("*")).toHaveAttribute("title", "* 12 of 82 games");
    expect(within(rows[0]).getAllByText("Free agent")).toHaveLength(1);
  });

  it("stacks a negative category left of zero and positives right of it", () => {
    render(<Leaderboard categories={board.categories} entries={board.entries} />);
    const zero = zeroX();
    const [, fgRight] = extent(segment("Rookie Ray", "FG%"));
    const [ptsLeft] = extent(segment("Rookie Ray", "PTS"));
    expect(fgRight).toBeLessThanOrEqual(zero + 0.5);
    expect(ptsLeft).toBeGreaterThanOrEqual(zero - 0.5);
  });

  it("shows hover text for segments and the net tick", () => {
    render(<Leaderboard categories={board.categories} entries={board.entries} />);
    expect(segment("Rookie Ray", "FG%").querySelector("title")).toHaveTextContent("Rookie Ray · FG% · −0.35");
    const titles = [...document.querySelectorAll('[data-testid="leaderboard-bars"] title')].map((t) => t.textContent);
    expect(titles).toContain("Steady Streamer · xLift +1.80");
  });

  it("colors each category from the qualitative palette, adjacent ones differing, readable at 0.10", () => {
    render(<Leaderboard categories={board.categories} entries={board.entries} />);
    const legend = screen.getByRole("list", { name: "Categories" });
    expect(within(legend).getAllByRole("listitem").map((li) => li.textContent)).toEqual(
      board.categories.map((c) => c.label),
    );
    const fills = board.categories.map((c) => segment("Steady Streamer", c.label).getAttribute("fill"));
    expect(fills).toEqual(CATEGORY_COLORS.slice(0, board.categories.length));
    for (let i = 1; i < fills.length; i++) expect(fills[i]).not.toBe(fills[i - 1]);
    const [l, r] = extent(segment("Steady Streamer", "STL")); // a 0.10 segment
    expect(r - l).toBeGreaterThanOrEqual(4);
  });

  it("says so when no player matches", () => {
    render(<Leaderboard categories={board.categories} entries={[]} />);
    expect(screen.getByText("No players match these filters.")).toBeInTheDocument();
    expect(screen.queryByTestId("leaderboard-bars")).toBeNull();
  });
});

describe("the Player Analysis page", () => {
  beforeEach(() => {
    sessionStorage.clear();
    leaderboardMock.mockClear();
  });

  it("requests the shared settings and no moves or mode", async () => {
    renderPage([{ type: "drop", player_id: 10, team_id: 4 }]);
    await screen.findAllByTestId("leaderboard-row", undefined, { timeout: 2000 });
    expect(lastRequest()).toEqual({
      league_id: 1,
      team_id: 4,
      window: 82,
      fragility: "dab_tag",
      evaluate_for: "team",
      pool: "free_agents",
      top: 25,
      min_games: 5,
    });
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Player Analysis");
    expect(screen.getByText(/Scored for Deltas · 3 of 4 players/)).toBeInTheDocument();
    expect(screen.getByText(/\* 12 of 82 games — Rookie Ray/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Reset/ })).toBeNull();
    // When the data was loaded, as in Impact Analysis; the leaderboard doesn't use the matchup.
    const dataLine = document.querySelector(".explainer .data-line")!;
    expect(dataLine).toHaveTextContent("Statistics last updated: 2026-11-18");
    expect(dataLine).toHaveTextContent("Rosters last updated: 2026-11-18");
    expect(dataLine).not.toHaveTextContent("Matchup");
  });

  it("sends each leaderboard control's value and shows the League scope line", async () => {
    renderPage();
    await screen.findAllByTestId("leaderboard-row", undefined, { timeout: 2000 });
    fireEvent.change(screen.getByLabelText("Evaluate for"), { target: { value: "league" } });
    fireEvent.click(screen.getByRole("radio", { name: "All players" }));
    fireEvent.change(screen.getByLabelText("Show top"), { target: { value: "50" } });
    fireEvent.change(screen.getByLabelText("Min games"), { target: { value: "10" } });
    await waitFor(() =>
      expect(lastRequest()).toMatchObject({ evaluate_for: "league", pool: "all", top: 50, min_games: 10 }),
    );
    expect(JSON.parse(sessionStorage.getItem("ffm.player-analysis.v1")!)).toEqual({
      evaluateFor: "league",
      pool: "all",
      top: 50,
      minGames: 10,
    });
  });

  it("picks the team in Evaluate for, with League as an option and no separate Team control", async () => {
    renderPage();
    await screen.findAllByTestId("leaderboard-row", undefined, { timeout: 2000 });
    expect(screen.queryByLabelText("Team")).toBeNull();
    const evaluateFor = screen.getByLabelText("Evaluate for") as HTMLSelectElement;
    expect(evaluateFor.value).toBe("4");
    const options = [...evaluateFor.options].filter((o) => !o.disabled).map((o) => o.textContent);
    expect(options[0]).toBe("League");
    expect(options.slice(1)).toEqual(league.teams.map((t) => `${t.name} — ${t.manager}`));
    fireEvent.change(evaluateFor, { target: { value: "league" } });
    await waitFor(() => expect(lastRequest()).toMatchObject({ evaluate_for: "league", team_id: 4 }));
    expect(evaluateFor.value).toBe("league");
    fireEvent.change(evaluateFor, { target: { value: "2" } });
    await waitFor(() => expect(lastRequest()).toMatchObject({ evaluate_for: "team", team_id: 2 }));
    // The team carries over to Impact Analysis.
    expect(JSON.parse(sessionStorage.getItem("ffm.impact.v3")!).settings.teamId).toBe(2);
  });

  it("shows the League scope line from the response", async () => {
    leaderboardMock.mockImplementation(async () => ({ ...structuredClone(board), evaluate_for: "league" }));
    renderPage();
    expect(
      await screen.findByText(/Averaged over every team but the player's own/, undefined, { timeout: 2000 }),
    ).toBeInTheDocument();
    leaderboardMock.mockImplementation(async () => structuredClone(board));
  });

  it("falls back to defaults for invalid stored settings", async () => {
    sessionStorage.setItem("ffm.player-analysis.v1", JSON.stringify({ top: 12, minGames: 99, pool: "x" }));
    renderPage();
    await screen.findAllByTestId("leaderboard-row", undefined, { timeout: 2000 });
    expect(lastRequest()).toMatchObject({ top: 25, min_games: 5, pool: "free_agents", evaluate_for: "team" });
  });
});
