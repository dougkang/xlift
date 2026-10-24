/** 004 content rules: concise (FR-009), ordered (FR-008), complete (FR-010), mode-aware (FR-011),
 * and quoting live numbers (FR-012). */
import { describe, expect, it } from "vitest";
import { HELP, helpText, wordCount, type HelpContext, type TopicId } from "../src/help/content";

const ctx = (mode: HelpContext["mode"], over: Partial<HelpContext> = {}): HelpContext => ({
  mode,
  iterations: 25000,
  window: 15,
  capacity: 13,
  opponentName: "Gammas",
  ...over,
});
const topics = Object.keys(HELP) as TopicId[];
const modes = ["strategic", "tactical"] as const;
const text = (id: TopicId, mode: HelpContext["mode"], over?: Partial<HelpContext>) =>
  helpText(HELP[id](ctx(mode, over)));

describe("help content", () => {
  it("covers all 9 topics", () => {
    expect(topics).toHaveLength(9);
  });

  it.each(modes.flatMap((m) => topics.map((t) => [t, m] as const)))("%s (%s) is at most 120 words", (t, m) => {
    expect(wordCount(text(t, m))).toBeLessThanOrEqual(120);
  });

  it("defines every FR-010 term somewhere", () => {
    const all = modes.flatMap((m) => topics.map((t) => text(t, m))).join("\n");
    for (const re of [
      /Aggregated Record/,
      /Chance to Win/,
      /H2H/,
      /Win %/,
      /Area score/,
      /min-max/,
      /Rank.*1 is best/,
      /lower-is-better/,
      /League:/,
      /Leader:/,
      /fewer games/,
      /G: games left/,
      /IL\/NA/,
      /makes ÷/,
      /[Gg]reen/,
      /red/,
      /dotted/,
      /\(before\)/,
    ]) {
      expect(all, String(re)).toMatch(re);
    }
  });

  it("names controls exactly as they appear on screen", () => {
    const s = HELP.settings(ctx("tactical")).controls!.map(([n]) => n);
    expect(s).toEqual(["Last X games", "League / Team", "vs", "Week", "Reset"]);
  });
});

describe("mode variants (US2)", () => {
  it.each(["headline", "categoryTable", "breakdown"] as const)("%s differs by mode", (t) => {
    expect(text(t, "strategic")).not.toEqual(text(t, "tactical"));
  });

  it("describes the version on screen", () => {
    expect(text("headline", "strategic")).toMatch(/Aggregated Record/);
    expect(text("headline", "tactical")).toMatch(/Chance to Win/);
    expect(text("headline", "tactical")).toMatch(/Choose an opponent/);
    for (const w of ["Rank", "Avg", "League", "Leader", "Win %"]) expect(text("categoryTable", "strategic")).toContain(w);
    for (const w of ["You / Opp", "Diff", "Win %"]) expect(text("categoryTable", "tactical")).toContain(w);
    expect(text("breakdown", "strategic")).toMatch(/League Leader and League Average/);
    expect(text("breakdown", "tactical")).toMatch(/opponent \(Gammas\)/);
  });

  it("adds vs, Week and G only in tactical", () => {
    expect(text("settings", "strategic")).not.toMatch(/\bvs\b|Week/);
    for (const t of ["roster", "players"] as const) {
      expect(text(t, "strategic")).not.toMatch(/G: games/);
      expect(text(t, "tactical")).toMatch(/G: games left this week/);
    }
  });

  it("quotes the numbers the page is using (FR-012)", () => {
    expect(text("settings", "strategic", { iterations: 12345 })).toContain("12,345");
    expect(text("settings", "strategic", { window: 7 })).toContain("now 7");
    expect(text("roster", "strategic", { capacity: 10 })).toContain("10 active slots");
  });
});
