import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../src/api/client";
import league from "./fixtures/league.json";
import leagues from "./fixtures/leagues.json";
import strategic from "./fixtures/strategic.json";

const page = {
  total: 3,
  players: [
    {
      player_id: 13, name: "Steady Streamer", nba_team: "MIA", positions: ["G"], owner_team_id: null,
      owner_label: "FA", status: "healthy", games_found: 15, games_requested: 15, games_remaining: null,
      footnote: null,
      eligibility: { can_add: false, add_blocked_reason: "No open active slot — drop a player first", swap_give_options: [] },
    },
    {
      player_id: 15, name: "Rookie Ray", nba_team: "CHI", positions: ["G"], owner_team_id: null,
      owner_label: "FA", status: "Q", games_found: 2, games_requested: 15, games_remaining: null,
      footnote: "* 2 of 15 games",
      eligibility: { can_add: false, add_blocked_reason: "No open active slot — drop a player first", swap_give_options: [] },
    },
    {
      player_id: 1, name: "Alpha One", nba_team: "BOS", positions: ["G"], owner_team_id: 1,
      owner_label: "Alphas", status: "healthy", games_found: 15, games_requested: 15, games_remaining: null,
      footnote: null,
      eligibility: { can_add: false, add_blocked_reason: "On Alphas: swap required", swap_give_options: ["roster"] },
    },
  ],
};

const analyze = vi.fn();
vi.mock("../src/api/client", async (orig) => {
  const actual = await orig<typeof import("../src/api/client")>();
  return {
    ...actual,
    listLeagues: vi.fn(async () => leagues),
    getLeague: vi.fn(async () => league),
    analyze: (...args: unknown[]) => analyze(...args),
    players: vi.fn(async () => page),
  };
});

const { default: App } = await import("../src/App");

type Req = { moves?: unknown[] };
const lastMoves = () => (analyze.mock.calls.at(-1)?.[0] as Req).moves;

describe("roster moves (US2)", () => {
  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem("ffm.impact.v2", JSON.stringify({ settings: { leagueId: 1, teamId: 4 }, moves: [] }));
    analyze.mockReset();
    analyze.mockImplementation(async () => strategic);
  });
  afterEach(cleanup);

  it("drop dispatches a move and re-requests; reset clears it", async () => {
    const user = userEvent.setup();
    render(<App />);
    const drop = await screen.findByRole("button", { name: "Drop Delta One" }, { timeout: 2000 });
    expect(screen.getByRole("button", { name: /^Reset/ })).toBeDisabled();
    await user.click(drop);
    await waitFor(() => expect(lastMoves()).toEqual([{ type: "drop", player_id: 10, team_id: 4 }]));
    const reset = screen.getByRole("button", { name: "Reset (1 move)" });
    await user.click(reset);
    await waitFor(() => expect(lastMoves()).toEqual([]));
  });

  it("disables + with the server's reason, and opens swap with allowed options only", async () => {
    const user = userEvent.setup();
    render(<App />);
    const add = await screen.findByRole("button", { name: "Add Steady Streamer" }, { timeout: 2000 });
    expect(add).toBeDisabled();
    expect(add).toHaveAttribute("title", "No open active slot — drop a player first");
    await user.click(screen.getByRole("button", { name: "Add Alpha One" }));
    const dialog = screen.getByRole("dialog", { name: "Swap for Alpha One" });
    expect(within(dialog).getByText("Your roster (trade)")).toBeInTheDocument();
    expect(within(dialog).queryByText("A free agent")).toBeNull();
    await user.click(within(dialog).getAllByRole("button", { name: "Give" })[0]);
    await waitFor(() =>
      expect(lastMoves()).toEqual([{ type: "swap", acquire_id: 1, give_id: 10, team_id: 4 }]),
    );
  });

  it("shows a rejected move inline and drops it", async () => {
    const user = userEvent.setup();
    analyze.mockImplementation(async (req: Req) => {
      if (req.moves?.length) {
        throw new ApiError(422, { move_index: 0, code: "NOT_ON_TEAM", message: "Player 10 is not on Deltas" });
      }
      return strategic;
    });
    render(<App />);
    await user.click(await screen.findByRole("button", { name: "Drop Delta One" }, { timeout: 2000 }));
    expect(await screen.findByText("Move not applied: Player 10 is not on Deltas")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: /^Reset/ })).toBeDisabled());
  });

  it("keeps moves across a remount via sessionStorage", async () => {
    const user = userEvent.setup();
    const { unmount } = render(<App />);
    await user.click(await screen.findByRole("button", { name: "Drop Delta One" }, { timeout: 2000 }));
    unmount();
    render(<App />);
    expect(await screen.findByRole("button", { name: "Reset (1 move)" })).toBeEnabled();
  });

  it("marks short-history players in the picker", async () => {
    render(<App />);
    await screen.findByRole("button", { name: "Add Rookie Ray" }, { timeout: 2000 });
    const picker = document.querySelector("table.picker-table") as HTMLElement;
    const row = within(picker).getByText("Rookie Ray").closest("tr")!;
    expect(within(row).getByText("*")).toHaveAttribute("title", "* 2 of 15 games");
    expect(row).toHaveTextContent("CHI Q");
    expect(within(row).getByText("Q", { exact: false, selector: ".status" })).toBeInTheDocument();
    expect(row.querySelectorAll("td")[2]).toHaveTextContent("G");
  });
});
