/** Player picker filters and category sort (013). */
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { PlayerPage, ScenarioRequest } from "../src/api/client";

type Any = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

const playersMock = vi.fn();
vi.mock("../src/api/client", async (orig) => {
  const actual = await orig<typeof import("../src/api/client")>();
  return { ...actual, players: (...args: unknown[]) => playersMock(...args) };
});
const { PlayerPicker } = await import("../src/components/PlayerPicker");

const request = { league_id: 1, team_id: 4, mode: "strategic" } as ScenarioRequest;
const teams = [
  { team_id: 1, name: "Alphas" },
  { team_id: 2, name: "Betas" },
];
const categories = [
  { key: "reb", label: "REB" },
  { key: "blk", label: "BLK" },
];
const row = (over: Any = {}) => ({
  player_id: 1,
  name: "Big Man",
  nba_team: "MIA",
  positions: ["C"],
  owner_team_id: null,
  owner_label: "FA",
  status: "healthy",
  games_found: 10,
  games_requested: 10,
  games_remaining: null,
  footnote: null,
  xlift: 1.5,
  sort_xlift: null,
  eligibility: { can_add: true, add_blocked_reason: null, swap_give_options: [] },
  ...over,
});
const last = () => playersMock.mock.calls.at(-1)![0] as Any;

function open(page: PlayerPage = { total: 1, players: [row()] } as unknown as PlayerPage) {
  playersMock.mockReset();
  playersMock.mockImplementation(async () => page);
  render(<PlayerPicker request={request} onAdd={() => {}} onSwap={() => {}} teams={teams} categories={categories} />);
}

describe("player picker filters (013)", () => {
  afterEach(cleanup);

  it("sends nothing picked by default", async () => {
    open();
    await waitFor(() => expect(last()).toMatchObject({ positions: [], owners: [], sort_categories: [] }));
  });

  it("position pills filter, several at once", async () => {
    open();
    const pos = screen.getByRole("group", { name: "Position" });
    fireEvent.click(within(pos).getByRole("button", { name: "C" }));
    fireEvent.click(within(pos).getByRole("button", { name: "G" }));
    await waitFor(() => expect(last().positions).toEqual(["C", "G"]));
    expect(within(pos).getByRole("button", { name: "C" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(within(pos).getByRole("button", { name: "C" }));
    await waitFor(() => expect(last().positions).toEqual(["G"]));
  });

  it("the Team checklist offers free agents and the other teams", async () => {
    open();
    fireEvent.click(screen.getByRole("button", { name: "Team" }));
    const menu = screen.getByRole("group", { name: "Teams" });
    expect(within(menu).getAllByRole("checkbox")).toHaveLength(3);
    fireEvent.click(within(menu).getByLabelText("Free agents"));
    fireEvent.click(within(menu).getByLabelText("Betas"));
    await waitFor(() => expect(last().owners).toEqual(["fa", 2]));
    expect(screen.getByRole("button", { name: "Team" })).toHaveTextContent("2 picked");
  });

  it("sort by categories adds a column named for them", async () => {
    open({ total: 1, players: [row({ sort_xlift: 0.8 })] } as unknown as PlayerPage);
    const sort = screen.getByRole("group", { name: "Sort by" });
    fireEvent.click(within(sort).getByRole("button", { name: "REB" }));
    fireEvent.click(within(sort).getByRole("button", { name: "BLK" }));
    await waitFor(() => expect(last().sort_categories).toEqual(["reb", "blk"]));
    expect(await screen.findByRole("columnheader", { name: "REB+BLK" })).toBeInTheDocument();
    expect(await screen.findByText("+0.80")).toBeInTheDocument();
  });

  it("says when nothing matches", async () => {
    open({ total: 0, players: [] } as unknown as PlayerPage);
    expect(await screen.findByText("No players match.")).toBeInTheDocument();
  });
});
