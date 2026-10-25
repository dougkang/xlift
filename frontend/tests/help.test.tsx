/** 004 US1/US2: every section has a "?" that opens its help, which closes on Esc or a click
 * outside, returning focus to the button; one help at a time; no extra layout. */
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
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

async function renderMode(mode: "strategic" | "tactical") {
  analyze.mockImplementation(async () => (mode === "tactical" ? tactical : strategic));
  sessionStorage.setItem(
    "ffm.impact.v3",
    JSON.stringify({ settings: { leagueId: 1, teamId: mode === "tactical" ? 3 : 4, mode }, moves: [] }),
  );
  render(<App />);
  await screen.findByRole("heading", { level: 2 }, { timeout: 2000 });
}

const STRATEGIC = [
  "Strategic / Tactical",
  "Analysis settings",
  "Aggregated Record",
  "Radar",
  "Per Category Ranking",
  "Roster",
  "H2H",
  "Category Breakdown",
  "Players",
];

describe("section help", () => {
  beforeEach(() => {
    sessionStorage.clear();
    analyze.mockReset();
  });
  afterEach(cleanup);

  it.each(STRATEGIC)("%s: opens, and closes via Esc and outside click with focus returned", async (title) => {
    const user = userEvent.setup();
    await renderMode("strategic");
    const btn = screen.getByRole("button", { name: `Help: ${title}` });
    expect(btn).toHaveAttribute("aria-haspopup", "dialog");

    for (const close of ["esc", "outside"] as const) {
      await user.click(btn);
      expect(btn).toHaveAttribute("aria-expanded", "true");
      const dlg = screen.getByRole("dialog", { name: title });
      expect(within(dlg).getByRole("heading", { name: title })).toHaveFocus();
      // Controls come before Reading it (FR-008).
      const labels = [...dlg.querySelectorAll(".col-header")].map((e) => e.textContent);
      expect(labels.indexOf("Reading it")).toBeGreaterThanOrEqual(0);
      if (labels.includes("Controls")) expect(labels.indexOf("Controls")).toBe(0);

      expect(within(dlg).queryByRole("button")).toBeNull(); // no close button
      if (close === "esc") await user.keyboard("{Escape}");
      else await user.click(document.querySelector("hr.section-rule")!);
      expect(screen.queryByRole("dialog")).toBeNull();
      await waitFor(() => expect(btn).toHaveFocus());
    }
  });

  it("keeps only one help open at a time", async () => {
    const user = userEvent.setup();
    await renderMode("strategic");
    await user.click(screen.getByRole("button", { name: "Help: Radar" }));
    await user.click(screen.getByRole("button", { name: "Help: H2H" }));
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
    expect(screen.getByRole("dialog", { name: "H2H" })).toBeInTheDocument();
  });

  it("strategic headline help explains the Aggregated Record with the live simulation count", async () => {
    const user = userEvent.setup();
    await renderMode("strategic");
    await user.click(screen.getByRole("button", { name: "Help: Aggregated Record" }));
    const dlg = screen.getByRole("dialog");
    expect(dlg).toHaveTextContent(`${strategic.settings.iterations.toLocaleString("en-US")} simulations`);
  });

  it("tactical shows the tactical variants (US2)", async () => {
    const user = userEvent.setup();
    await renderMode("tactical");
    await user.click(screen.getByRole("button", { name: "Help: Chance to Win" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Now is the category score so far");
    await user.click(screen.getByRole("button", { name: "Help: Per Category Difference" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("You / Opp");
    await user.click(screen.getByRole("button", { name: "Help: Analysis settings" }));
    expect(screen.getByRole("dialog")).not.toHaveTextContent("Week");
    // The opponent's roster replaces H2H, with its own help (005).
    await user.click(screen.getByRole("button", { name: "Help: Deltas roster" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("read-only");
  });

  it("help buttons sit inline in their headings and add no blocks (FR-003)", async () => {
    await renderMode("strategic");
    const buttons = [...document.querySelectorAll("button.help-button")];
    expect(buttons).toHaveLength(9);
    for (const b of buttons) {
      expect(b.closest("h3.section-divider, .units, .controls-row, .mode-toggle")).not.toBeNull();
    }
    expect(screen.getByRole("heading", { name: /^Radar/ }).childElementCount).toBe(1);
  });

  it("shows only the mode, settings and Players help before there is a result", async () => {
    analyze.mockImplementation(() => new Promise(() => {}));
    sessionStorage.setItem("ffm.impact.v3", JSON.stringify({ settings: { leagueId: 1, teamId: 4 }, moves: [] }));
    render(<App />);
    await screen.findByRole("button", { name: "Help: Analysis settings" });
    expect(document.querySelectorAll("button.help-button")).toHaveLength(3); // mode, settings and Players
    expect(screen.queryByRole("button", { name: "Help: H2H" })).toBeNull();
  });
});
