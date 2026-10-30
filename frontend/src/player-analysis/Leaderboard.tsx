import * as Plot from "@observablehq/plot";
import { useEffect, useRef, useState } from "react";
import type { LeaderboardCategory, LeaderboardEntry } from "../api/client";
import { formatXlift } from "../format";

/** docs/style.md "Simple, Qualitative Categorization with higher Dimensions", in category order. */
export const CATEGORY_COLORS = [
  "#a6cee3",
  "#1f78b4",
  "#b2df8a",
  "#33a02c",
  "#fb9a99",
  "#e31a1c",
  "#fdbf6f",
  "#ff7f00",
  "#cab2d6",
];

/** Shared by the label column and the plot, so each label sits on its bar (009 analysis U2). */
export const ROW_HEIGHT = 18;
export const AXIS_HEIGHT = 30;
const MARGIN_BOTTOM = 4;
const DEFAULT_WIDTH = 640;

const color = (i: number) => CATEGORY_COLORS[i % CATEGORY_COLORS.length];

interface Segment {
  pid: string;
  name: string;
  c: number;
  label: string;
  v: number;
}

/** The xLift leaderboard (009 contracts/ui.md "Chart"): one row per player in the server's
 * order, segments stacked by category (negatives left of zero), a tick at the net. Draws only. */
export function Leaderboard({
  categories,
  entries,
  yours = null,
}: {
  /** The team being evaluated for: its players are marked as yours, for comparison. */
  yours?: number | null;
  categories: LeaderboardCategory[];
  entries: LeaderboardEntry[];
}) {
  if (!entries.length) return <p className="leaderboard-empty">No players match these filters.</p>;
  return (
    <div className="leaderboard">
      <ul className="leaderboard-legend" aria-label="Categories">
        {categories.map((c, i) => (
          <li key={c.key}>
            <span className="swatch" style={{ background: color(i) }} />
            {c.label}
          </li>
        ))}
      </ul>
      <div className="leaderboard-grid">
        <ol className="leaderboard-labels" style={{ paddingTop: AXIS_HEIGHT }}>
          {entries.map((e) => (
            <li
              key={e.player_id}
              style={{ height: ROW_HEIGHT }}
              data-testid="leaderboard-row"
              className={yours !== null && e.owner_team_id === yours ? "yours" : undefined}
            >
              <span className="name-col">{e.name}</span>
              <span className="owner">{e.owner_label}</span>
              {e.status !== "healthy" && <span className="status">{e.status}</span>}
              <span className="net">
                {formatXlift(e.xlift)}
                {e.footnote && (
                  <sup className="marker" title={e.footnote}>
                    *
                  </sup>
                )}
              </span>
            </li>
          ))}
        </ol>
        <Bars categories={categories} entries={entries} />
      </div>
    </div>
  );
}

function Bars({ categories, entries }: { categories: LeaderboardCategory[]; entries: LeaderboardEntry[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => {
      const w = Math.floor(entry.contentRect.width);
      if (w > 0) setWidth(w);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ids = entries.map((e) => String(e.player_id));
    const segments: Segment[] = entries.flatMap((e) =>
      e.by_category.map((v, c) => ({
        pid: String(e.player_id),
        name: e.name,
        c,
        label: categories[c]?.label ?? "",
        v,
      })),
    );
    const nets = entries.map((e) => ({ pid: String(e.player_id), name: e.name, x: e.xlift }));
    const chart = Plot.plot({
      width,
      height: AXIS_HEIGHT + entries.length * ROW_HEIGHT + MARGIN_BOTTOM,
      marginTop: AXIS_HEIGHT,
      marginBottom: MARGIN_BOTTOM,
      marginLeft: 4,
      marginRight: 12,
      style: { fontFamily: "Helvetica Neue, Helvetica, Arial, sans-serif", fontSize: "10px" },
      x: { axis: "top", label: "Weekly category wins added", ticks: 5, labelAnchor: "left" },
      y: { domain: ids, axis: null, padding: 0.2 },
      color: { type: "identity" },
      marks: [
        // Stacked by category in format order; Plot stacks negatives left of zero separately.
        Plot.barX(segments, {
          x: "v",
          y: "pid",
          fill: (d: Segment) => color(d.c),
          title: (d: Segment) => `${d.name} · ${d.label} · ${formatXlift(d.v)}`,
        }),
        Plot.ruleX([0], { stroke: "#ccc" }),
        // The net: black over a white halo, so it reads on every segment (docs/style.md).
        Plot.tickX(nets, { x: "x", y: "pid", stroke: "#fff", strokeWidth: 4 }),
        Plot.tickX(nets, {
          x: "x",
          y: "pid",
          stroke: "#111",
          strokeWidth: 2,
          title: (d: { name: string; x: number }) => `${d.name} · xLift ${formatXlift(d.x)}`,
        }),
      ],
    });
    el.replaceChildren(chart);
    return () => chart.remove();
  }, [categories, entries, width]);
  return <div ref={ref} className="leaderboard-bars" data-testid="leaderboard-bars" />;
}
