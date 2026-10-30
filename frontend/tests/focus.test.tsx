/** Focus on an H2H opponent (011): clicking a row compares the page with that team. */
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import league from "./fixtures/league.json";
import leagues from "./fixtures/leagues.json";
import strategic from "./fixtures/strategic.json";
import strategicFocus from "./fixtures/strategic_focus.json";
import type { Move } from "../src/api/client";
import { initialState, reducer, type Action, type ScenarioState } from "../src/state/scenario";

type Any = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

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

const lastFocus = () => (analyze.mock.calls.at(-1)![0] as Any).focus_opponent_id;
const row = (name: string) => screen.getByRole("button", { name: new RegExp(`^${name}`) }).closest("tr")!;

async function open() {
  render(<App />);
  await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
  return document.querySelector("table.record-table") as HTMLElement;
}

describe("focus on an H2H opponent (011)", () => {
  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem(
      "ffm.impact.v3",
      JSON.stringify({ settings: { leagueId: 1, teamId: 4, mode: "strategic" }, moves: [] }),
    );
    // The server answers with the focused view when asked for one.
    analyze.mockReset();
    analyze.mockImplementation(async (req: Any) => (req.focus_opponent_id === 1 ? strategicFocus : strategic));
  });
  afterEach(cleanup);

  it("clicking a row asks for that opponent and draws the matchup", async () => {
    const user = userEvent.setup();
    await open();
    expect(lastFocus()).toBeNull();
    await user.click(within(row("Alphas")).getAllByRole("cell")[1]); // anywhere on the row
    await waitFor(() => expect(lastFocus()).toBe(1), { timeout: 2000 });
    expect(row("Alphas")).toHaveClass("opponent-row");
    expect(within(row("Alphas")).getByRole("button")).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(screen.getAllByTestId(/^radar-(selected|other|opponent)$/)).toHaveLength(2));
    expect(screen.getByTestId("radar-opponent")).toBeInTheDocument();
    expect(document.querySelector('[data-testid="radar-league_average"]')).toBeNull();
    const table = document.querySelector(".category-table") as HTMLElement;
    expect(within(table).getByText("Alphas")).toHaveAttribute("title", "Alphas");
    expect(within(table).queryByText("League")).toBeNull();
    const legend = document.querySelectorAll(".curve-legend")[1] ?? document.querySelector(".curve-legend");
    expect(document.body.textContent).toContain("Alphas");
    expect(legend).toBeTruthy();
  });

  it("clicking the focused row again returns to the league; another row moves the focus", async () => {
    const user = userEvent.setup();
    await open();
    await user.click(within(row("Alphas")).getByRole("button"));
    await waitFor(() => expect(lastFocus()).toBe(1), { timeout: 2000 });
    await user.click(within(row("Betas")).getByRole("button"));
    await waitFor(() => expect(lastFocus()).toBe(2), { timeout: 2000 });
    expect(row("Betas")).toHaveClass("opponent-row");
    expect(row("Alphas")).not.toHaveClass("opponent-row");
    await user.click(within(row("Betas")).getByRole("button"));
    await waitFor(() => expect(lastFocus()).toBeNull(), { timeout: 2000 });
  });

  it("the keyboard reaches each row's button", async () => {
    const user = userEvent.setup();
    await open();
    const button = within(row("Gammas")).getByRole("button");
    button.focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(lastFocus()).toBe(3), { timeout: 2000 });
  });
});

describe("focus state (011 FR-004)", () => {
  const focused: ScenarioState = {
    ...initialState,
    settings: { ...initialState.settings, leagueId: 1, teamId: 4 },
    focusOpponentId: 2,
  };
  const after = (a: Action) => reducer(focused, a).focusOpponentId;
  const move: Move = { type: "drop", player_id: 9, team_id: 4 };

  it("clears on league, team or mode", () => {
    expect(after({ type: "setLeague", leagueId: 1 })).toBeNull();
    expect(after({ type: "setTeam", teamId: 3 })).toBeNull();
    expect(after({ type: "setMode", mode: "tactical" })).toBeNull();
  });

  it("stays through moves, undo, reset, window, Fragility Penalty and radar scale", () => {
    expect(after({ type: "addMove", move })).toBe(2);
    expect(reducer({ ...focused, moves: [move] }, { type: "popMove" }).focusOpponentId).toBe(2);
    expect(after({ type: "reset" })).toBe(2);
    expect(after({ type: "setWindow", window: 20 })).toBe(2);
    expect(after({ type: "setFragility", fragility: "none" })).toBe(2);
    expect(after({ type: "setRadarScale", scale: "rank" })).toBe(2);
  });

  it("toggles, and isn't saved", () => {
    expect(after({ type: "toggleFocus", opponentId: 2 })).toBeNull();
    expect(after({ type: "toggleFocus", opponentId: 1 })).toBe(1);
  });
});
