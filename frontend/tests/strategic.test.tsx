import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import league from "./fixtures/league.json";
import leagues from "./fixtures/leagues.json";
import strategic from "./fixtures/strategic.json";

vi.mock("../src/api/client", async (orig) => {
  const actual = await orig<typeof import("../src/api/client")>();
  return {
    ...actual,
    listLeagues: vi.fn(async () => leagues),
    getLeague: vi.fn(async () => league),
    analyze: vi.fn(async () => strategic),
  };
});

const { default: App } = await import("../src/App");

describe("strategic view (US1)", () => {
  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem(
      "ffm.impact.v1",
      JSON.stringify({ settings: { leagueId: 1, teamId: 4 }, moves: [] }),
    );
  });

  it("shows record headline with units", async () => {
    render(<App />);
    const h = await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
    expect(h).toHaveTextContent("Deltas");
    const header = h.closest("header")!;
    expect(within(header).getByText("Di")).toHaveClass("manager");
    expect(within(header).getByLabelText("Projected record")).toHaveTextContent("0–3–0");
    expect(header.closest("main")).toBeNull(); // spans main + sidebar
    expect(screen.getByText("Aggregated Record")).toHaveAttribute("title", "W–L–T vs 3 teams");
  });

  it("renders radar, rank table, curves, and footnotes", async () => {
    render(<App />);
    await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
    const radar = screen.getByRole("img", { name: "Category rank radar" });
    expect(within(radar as unknown as HTMLElement).getAllByTestId(/radar-/)).toHaveLength(4);
    expect(radar.querySelector('[data-testid="radar-selected"]')).toHaveAttribute("stroke", "var(--sel)");
    const table = document.querySelector(".category-table")!;
    expect(table.querySelectorAll("tbody tr")).toHaveLength(9);
    expect(within(table as HTMLElement).getByText("League")).toBeInTheDocument();
    expect(within(table as HTMLElement).getAllByText("Leader")).toHaveLength(1);
    expect(within(table as HTMLElement).getByText("Win %")).toBeInTheDocument();
    expect(screen.getByText("Radar")).toBeInTheDocument();
    expect(screen.getByText("Per Category Ranking")).toBeInTheDocument();
    expect(table.querySelector("tbody td")).toHaveClass("name-col");
    expect(screen.getAllByTestId("curve")).toHaveLength(9);
    const footnote = screen.getByText(/\* 2 of 15 games — Rookie Ray/);
    expect(footnote.closest("section")).toContainElement(document.querySelector("table.roster"));
    const recordTable = document.querySelector("table.record-table")!;
    expect(recordTable.querySelectorAll("tbody tr")).toHaveLength(3);
    expect(recordTable.querySelector("tfoot .total-record")).toHaveTextContent("0–3–0");
    const firstCurve = screen.getAllByTestId("curve")[0];
    expect(within(firstCurve).getByText(/^You /)).toBeInTheDocument();
    expect(within(firstCurve).getByText(/^League /)).toBeInTheDocument();
    const rookieRow = screen.getAllByText("Rookie Ray")[0].closest("tr")!;
    expect(within(rookieRow).getByText("*")).toBeInTheDocument();
  });
});

describe("explainer", () => {
  it("states the simulation count from the result", async () => {
    sessionStorage.setItem("ffm.impact.v1", JSON.stringify({ settings: { leagueId: 1, teamId: 4 }, moves: [] }));
    render(<App />);
    await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
    const n = (strategic as { settings: { iterations: number } }).settings.iterations.toLocaleString("en-US");
    expect(screen.getByText(new RegExp(`simulation of ${n} matchup weeks per team`))).toBeInTheDocument();
  });
});

describe("radar scale", () => {
  it("switches between rank and normalized average", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    sessionStorage.setItem("ffm.impact.v1", JSON.stringify({ settings: { leagueId: 1, teamId: 4 }, moves: [] }));
    render(<App />);
    await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
    // Compare every series: the fixture's selected team (Deltas) is last everywhere, so its own
    // shape is the same in both scales; the middle teams move.
    const path = () =>
      Array.from(document.querySelectorAll('[data-testid^="radar-"]'))
        .map((p) => p.getAttribute("d"))
        .join("|");
    // Win % is the default scale.
    expect(screen.getByRole("radio", { name: /^Win %/ })).toHaveAttribute("aria-checked", "true");
    const sel = (strategic as { radar: { series: { emphasis: string; area: { rank: number } }[] } }).radar.series.find(
      (s) => s.emphasis === "selected",
    )!;
    expect(screen.getByRole("radio", { name: /^Rank/ })).toHaveTextContent(String(Math.round(sel.area.rank * 100)));
    const byWin = path();
    await user.click(screen.getByRole("radio", { name: /^Rank/ }));
    expect(screen.getByRole("radio", { name: /^Rank/ })).toHaveAttribute("aria-checked", "true");
    expect(path()).not.toBe(byWin);
    const byRank = path();
    await user.click(screen.getByRole("radio", { name: /^Average/ }));
    expect(path()).not.toBe(byRank);
  });
});
