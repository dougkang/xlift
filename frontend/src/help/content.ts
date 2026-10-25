/**
 * Section help copy (004). The single place to update when a section's behavior changes
 * (FR-013). Numbers come from the values the page is using (FR-012).
 */

export type TopicId =
  | "mode"
  | "settings"
  | "headline"
  | "radar"
  | "categoryTable"
  | "roster"
  | "opponentRoster"
  | "h2h"
  | "breakdown"
  | "players";

export interface HelpContext {
  mode: "strategic" | "tactical";
  /** Null until the first result arrives. */
  iterations: number | null;
  window: number;
  capacity: number | null;
  opponentName: string | null;
  /** The imported matchup's as-of date (005); null when none is loaded. */
  asOf: string | null;
}

export interface HelpTopic {
  title: string;
  /** [control name as on screen, what it changes] */
  controls?: [string, string][];
  reading: string[];
  /** [term, definition] */
  terms?: [string, string][];
}

const fmt = (n: number | null) => (n === null ? "thousands of" : n.toLocaleString("en-US"));
const BEFORE = "Green is better, red is worse; the change sits on the line below.";

export const HELP: Record<TopicId, (ctx: HelpContext) => HelpTopic> = {
  mode: () => ({
    title: "Strategic / Tactical",
    controls: [
      ["Strategic", "the long run: your team against every other team in the league."],
      ["Tactical", "this week: your current matchup against this week's opponent."],
    ],
    reading: [
      "Strategic plays a typical week: about 3 games per player, fewer for players who often miss games.",
      "Tactical adds the games each player has left to the stats already played this week.",
      "Tactical is unavailable until this week's matchup has been loaded.",
      "Strategic shows the Aggregated Record, Per Category Ranking and league overlays.",
      "Tactical shows Chance to Win, Per Category Difference and your opponent's overlay.",
    ],
  }),

  settings: (ctx) => ({
    title: "Analysis settings",
    controls: [
      ["Last X games", `the most games each projection draws on (now ${ctx.window}); recent games count more, and last season's count less. Small samples are pulled toward a typical player.`],
      ["League / Team", "whose team you're analyzing; in tactical, its current opponent comes with it."],
      ["Reset", "undo every roster move."],
    ],
    reading: [
      `Every number comes from simulating ${fmt(ctx.iterations)} matchup weeks.`,
      "Moves are hypothetical and never change your real league.",
    ],
  }),

  headline: (ctx) =>
    ctx.mode === "strategic"
      ? {
          title: "Aggregated Record",
          reading: [
            "Your projected W–L–T if you played every other team once.",
            "The number below is the change in wins from your moves.",
          ],
          terms: [
            [
              "Aggregated Record",
              `a matchup is a W if you win it in more than half of ${fmt(ctx.iterations)} simulations.`,
            ],
          ],
        }
      : {
          title: "Chance to Win",
          reading: [
            `The line under your team names this week's opponent${ctx.opponentName ? ` (${ctx.opponentName})` : ""}.`,
            `Now is the category score so far${ctx.asOf ? `, as of ${ctx.asOf}` : ""}; Final once the week is over.`,
            "Green or red below shows the change from your moves.",
          ],
          terms: [
            [
              "Chance to Win",
              `how often you win the matchup across ${fmt(ctx.iterations)} simulations: stats so far plus the games left.`,
            ],
          ],
        },

  radar: () => ({
    title: "Radar",
    controls: [
      ["Rank / Average / Win %", "how far out each spoke goes; the league's best is at the edge."],
      ["Score on each tab", "your area score for that scale."],
    ],
    reading: [
      "Your team is navy; other teams are outlines.",
      "Where another outline pokes past yours, that team beats you in the category.",
      "A dotted outline is your shape before moves.",
    ],
    terms: [
      ["Area score", "your shape's area relative to the league's largest; the top team is 100."],
      ["Average", "each category min-max scaled across the league."],
      ["Rank", "1 is best; TO ranks lower-is-better."],
    ],
  }),

  categoryTable: (ctx) =>
    ctx.mode === "strategic"
      ? {
          title: "Per Category Ranking",
          reading: [
            "Rank: 1 is best.",
            "Avg: your projected weekly total.",
            "League: the league average. Leader: the best team's average; hover it to see the team.",
            BEFORE,
          ],
          terms: [["Win %", "your chance of beating a random league team in this category; ties count half."]],
        }
      : {
          title: "Per Category Difference",
          reading: [
            "Now: the week-to-date values, you–opponent.",
            "You / Opp: projected final totals, so far plus the games left.",
            "Diff: green favors you, red favors them.",
            "Changes from your moves sit on the line below.",
          ],
          terms: [["Win %", "your chance of winning this category against this opponent; ties count half."]],
        },

  roster: (ctx) => ({
    title: "Roster",
    controls: [["−", "drops a player to free agency (hypothetical)."]],
    reading: [
      ...(ctx.capacity ? [`${ctx.capacity} active slots play in the simulation.`] : []),
      "Muted rows are IL/NA reserve slots; they don't play.",
      "Red text is the player's status. Yellow rows were changed by your moves.",
      ...(ctx.mode === "tactical" ? ["G: games left this week."] : []),
    ],
    terms: [["*", "fewer games in the window than requested."]],
  }),

  opponentRoster: (ctx) => ({
    title: ctx.opponentName ? `${ctx.opponentName} roster` : "Opponent's roster",
    reading: [
      "Your opponent's players this week, read-only: moves apply only to your team.",
      "Muted rows are IL/NA reserve slots; red text is status.",
      "G: games left this week.",
    ],
  }),

  h2h: () => ({
    title: "H2H",
    reading: [
      "One row per opponent; Total sums every row.",
      "H2H: projected categories won–lost–tied against them in the simulations.",
      "Win: your chance to win the matchup.",
      "Result: W if you win in more than half the simulations. A bold green W means your moves turned a loss into a win; bold red, the reverse.",
    ],
  }),

  breakdown: (ctx) => ({
    title: "Category Breakdown",
    reading: [
      "Each chart shows the spread of your simulated weekly totals; lines mark averages.",
      ctx.mode === "strategic"
        ? "League Leader and League Average are overlaid."
        : `Your opponent${ctx.opponentName ? ` (${ctx.opponentName})` : ""} is overlaid.`,
      "A dotted \"(before)\" shape is your distribution before moves.",
    ],
    terms: [["FG% / FT%", "total makes ÷ total attempts, not an average of percentages."]],
  }),

  players: (ctx) => ({
    title: "Players",
    controls: [
      ["Search", "filter by name; accents are ignored."],
      ["+", "adds a free agent to an open slot. On another team's player, it opens a swap: give a roster player (a trade) or a free agent."],
    ],
    reading: [
      "Free agents are listed first. Red text is status; * means a short history.",
      ...(ctx.mode === "tactical" ? ["G: games left this week."] : []),
    ],
  }),
};

/** Plain text of a topic, for word counting. */
export function helpText(t: HelpTopic): string {
  return [
    t.title,
    ...(t.controls ?? []).flat(),
    ...t.reading,
    ...(t.terms ?? []).flat(),
  ].join(" ");
}

export function wordCount(text: string): number {
  return text.split(/\s+/).filter((w) => /[\p{L}\p{N}]/u.test(w)).length;
}
