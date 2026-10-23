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
    expect(screen.getByText("vs 3 teams (W–L–T)")).toBeInTheDocument();
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
    expect(screen.getByText("Category Ranks")).toBeInTheDocument();
    expect(screen.getByText("Per Category Ranking")).toBeInTheDocument();
    expect(table.querySelector("tbody td")).toHaveClass("name-col");
    expect(screen.getAllByTestId("curve")).toHaveLength(9);
    const footnote = screen.getByText(/\* 2 of 15 games — Rookie Ray/);
    expect(footnote.closest("section")).toContainElement(document.querySelector("table.roster"));
    const recordTable = document.querySelector("table.record-table")!;
    expect(recordTable.querySelectorAll("tbody tr")).toHaveLength(3);
    expect(within(recordTable.querySelector("tfoot")! as HTMLElement).getByText("0–3–0")).toBeInTheDocument();
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
