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
  asOf: "2026-11-18",
  ...over,
});
const topics = Object.keys(HELP) as TopicId[];
const modes = ["strategic", "tactical"] as const;
const text = (id: TopicId, mode: HelpContext["mode"], over?: Partial<HelpContext>) =>
  helpText(HELP[id](ctx(mode, over)));

describe("help content", () => {
  it("covers all 12 topics", () => {
    expect(topics).toHaveLength(12);
  });

  it.each(modes.flatMap((m) => topics.map((t) => [t, m] as const)))("%s (%s) is at most 120 words", (t, m) => {
    expect(wordCount(text(t, m))).toBeLessThanOrEqual(120);
  });

  it.each(modes.flatMap((m) => topics.map((t) => [t, m] as const)))(
    "%s (%s, each category) is at most 120 words and names no files",
    (t, m) => {
      const words = text(t, m, { standings: "category" });
      expect(wordCount(words)).toBeLessThanOrEqual(120);
      expect(words).not.toMatch(/\.csv|import/i);
    },
  );

  it.each(modes.flatMap((m) => topics.map((t) => [t, m] as const)))(
    "%s (%s, focused on an opponent) is at most 120 words",
    (t, m) => {
      const long = "Peter Piper Picked a Pick&Roll";
      expect(wordCount(text(t, m, { focusName: long, standings: "category" }))).toBeLessThanOrEqual(120);
      expect(wordCount(text(t, m, { focusName: long }))).toBeLessThanOrEqual(120);
    },
  );

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
    expect(s).toEqual(["Last X games", "Fragility Penalty", "League / Team", "Reset"]);
  });
});

describe("mode variants (US2)", () => {
  it.each(["headline", "categoryTable", "breakdown"] as const)("%s differs by mode", (t) => {
    expect(text(t, "strategic")).not.toEqual(text(t, "tactical"));
  });

  it("describes the version on screen", () => {
    expect(text("headline", "strategic")).toMatch(/Aggregated Record/);
    expect(text("headline", "tactical")).toMatch(/Chance to Win/);
    expect(text("headline", "tactical")).toMatch(/Now is the category score so far, as of 2026-11-18/);
    for (const w of ["Rank", "Avg", "League", "Leader", "Win %"]) expect(text("categoryTable", "strategic")).toContain(w);
    for (const w of ["Now", "You / Opp", "Diff", "Win %"]) expect(text("categoryTable", "tactical")).toContain(w);
    expect(text("breakdown", "strategic")).toMatch(/League Leader and League Average/);
    expect(text("breakdown", "tactical")).toMatch(/opponent \(Gammas\)/);
  });

  it("has no vs or Week controls (005) and adds G only in tactical", () => {
    for (const m of modes) expect(text("settings", m)).not.toMatch(/\bvs\b|Week/);
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

describe("current matchup (005)", () => {
  it("explains tactical as the current matchup, without mentioning files", () => {
    expect(text("mode", "tactical")).toMatch(/your current matchup against this week's opponent/);
    for (const m of modes) for (const t of topics) expect(text(t, m)).not.toMatch(/\.csv|import/i);
    expect(text("mode", "tactical")).toMatch(/stats already played this week/);
  });

  it("says the opponent's roster is read-only", () => {
    expect(text("opponentRoster", "tactical")).toMatch(/read-only/);
    expect(HELP.opponentRoster(ctx("tactical")).title).toBe("Gammas roster");
  });
});
