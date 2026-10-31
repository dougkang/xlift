import * as Plot from "@observablehq/plot";
import { useEffect, useRef, useState } from "react";
import type { AnalysisResult, Schemas } from "../api/client";
import { HelpButton } from "../help/HelpButton";
import { AgainstNullChart, LeagueShapeChart } from "./LeagueShape";

type Curve = Schemas["Curve"];
type Role = Schemas["CurveSeries"]["role"];

const STROKE: Record<Role, string> = {
  selected: "#1c324a",
  leader: "#ce7955",
  next_best: "#ce7955",
  league_average: "#898240",
  opponent: "#a96043",
  selected_original: "#aaa",
};

/** Lighter shade from the same palette, used for fills (docs/style.md). */
const FILL: Record<Role, string> = {
  selected: "#9dc0f5",
  leader: "#f5c1a9",
  next_best: "#f5c1a9",
  league_average: "#c5be60",
  opponent: "#f5c1a9",
  selected_original: "#eee",
};

/** The selected team's original (before-move) distribution, grayed out behind everything (003 R5). */
const ORIGINAL_ROLES: Role[] = ["selected_original"];
const TONE_COLOR = { better: "#5c8e4e", worse: "#c00", neutral: "#555" } as const;

/** League-related distributions get dotted average lines. */
const LEAGUE_ROLES: Role[] = ["leader", "next_best", "league_average"];

const SHORT: Record<Role, string> = {
  selected: "You",
  leader: "Leader",
  next_best: "Next best",
  league_average: "League",
  opponent: "Opp",
  selected_original: "Original",
};

const LABEL_ROW = 11;
const DEFAULT_WIDTH = 220;
const MARGIN = 8;
const CHAR_PX = 5.8; // approx. width of a 10px bold Helvetica character

interface Placed {
  x: number;
  role: Role;
  text: string;
  delta?: string;
  anchor: "start" | "end";
  row: number;
}

/**
 * Jitter labels vertically only when they would collide: each label goes in the lowest row
 * where its estimated pixel extent doesn't overlap a label already placed there.
 */
export function placeLabels(
  marks: { x: number; role: Role; text: string; delta?: string }[],
  domain: [number, number],
  width: number = DEFAULT_WIDTH,
): Placed[] {
  const [d0, d1] = domain;
  const span = d1 - d0 || 1;
  const inner = width - 2 * MARGIN;
  const rows: [number, number][][] = [];
  return marks.map((m) => {
    const px = MARGIN + ((m.x - d0) / span) * inner;
    const w = (m.text.length + (m.delta ? m.delta.length + 1 : 0)) * CHAR_PX + 4;
    const anchor: "start" | "end" = px > width / 2 ? "end" : "start";
    const extent: [number, number] = anchor === "start" ? [px - 2, px + w] : [px - w, px + 2];
    let row = rows.findIndex((r) => r.every(([a, b]) => extent[1] < a || extent[0] > b));
    if (row === -1) {
      rows.push([]);
      row = rows.length - 1;
    }
    rows[row].push(extent);
    return { ...m, anchor, row };
  });
}

type MeanChanges = Record<string, Schemas["Change"] | null | undefined>;

function CurveChart({
  curve,
  label,
  decimals,
  meanChanges,
  cat,
  shape,
}: {
  curve: Curve;
  label: string;
  decimals: number;
  meanChanges?: MeanChanges;
  cat: Schemas["CategoryInfo"];
  /** Strategic only (008): League shape and Against null under the distribution. */
  shape?: Schemas["CategoryShape"];
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  // Fill the grid cell: track the container's width.
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
    if (!curve.x.length) {
      el.textContent = "–";
      return;
    }
    const rows = curve.series.flatMap((s) =>
      s.density.map((d, i) => ({ x: curve.x[i], y: d, role: s.role, label: s.label })),
    );
    // Originals first (grayed, behind), then overlays, then the selected team on top.
    const layer = (r: Role) => (ORIGINAL_ROLES.includes(r) ? 0 : r === "selected" ? 2 : 1);
    const order = [...curve.series].sort((a, b) => layer(a.role) - layer(b.role));
    const fmt = (v: number) =>
      decimals > 0 ? v.toFixed(decimals).replace(/^0(?=\.)/, "") : v.toFixed(1);
    const domain: [number, number] = [curve.x[0], curve.x[curve.x.length - 1]];
    const deltaText = (role: Role) => {
      const ch = meanChanges?.[role];
      if (!ch) return undefined;
      const abs = Math.abs(ch.delta).toFixed(decimals > 0 ? decimals : 1);
      return `${ch.delta > 0 ? "+" : "−"}${decimals > 0 ? abs.replace(/^0(?=\.)/, "") : abs}`;
    };
    const means = placeLabels(
      curve.series
        .filter((s) => s.mean !== null && !ORIGINAL_ROLES.includes(s.role))
        .map((s) => ({
          x: s.mean as number,
          role: s.role,
          text: `${SHORT[s.role]} ${fmt(s.mean as number)}`,
          delta: deltaText(s.role),
        })),
      domain,
      width,
    );
    const rowCount = Math.max(1, ...means.map((m) => m.row + 1));
    const chart = Plot.plot({
      width,
      height: 110 + rowCount * LABEL_ROW,
      marginTop: 4 + rowCount * LABEL_ROW,
      marginLeft: MARGIN,
      marginRight: MARGIN,
      style: { fontFamily: "Helvetica Neue, Helvetica, Arial, sans-serif", fontSize: "10px" },
      x: {
        domain,
        label: null,
        ticks: 3,
        tickFormat: decimals > 0 ? (v: number) => v.toFixed(decimals).replace(/^0(?=\.)/, "") : undefined,
      },
      y: { axis: null },
      marks: [
        ...order.map((s) =>
          Plot.areaY(
            rows.filter((r) => r.role === s.role),
            {
              x: "x",
              y: "y",
              fill: FILL[s.role],
              fillOpacity: s.role === "selected" ? 0.6 : ORIGINAL_ROLES.includes(s.role) ? 1 : 0.4,
            },
          ),
        ),
        Plot.ruleX(
          means.filter((m) => !LEAGUE_ROLES.includes(m.role)),
          { x: "x", stroke: (m: { role: Role }) => STROKE[m.role], strokeWidth: 1.5 },
        ),
        Plot.ruleX(
          means.filter((m) => LEAGUE_ROLES.includes(m.role)),
          { x: "x", stroke: (m: { role: Role }) => STROKE[m.role], strokeWidth: 1.5, strokeDasharray: "2,3" },
        ),
        // One label per average line, stacked above the plot so they never collide. A change
        // (e.g. "+18.0") follows the label in its tone color; label + change are placed as one.
        ...means.flatMap((m) => {
          const dy = -(rowCount - m.row - 0.5) * LABEL_ROW;
          const deltaW = m.delta ? (m.delta.length + 1) * CHAR_PX : 0;
          const textW = m.text.length * CHAR_PX;
          const tone = meanChanges?.[m.role]?.tone ?? "neutral";
          const marks = [
            Plot.text([m], {
              x: "x",
              frameAnchor: "top",
              dy,
              text: "text",
              fill: STROKE[m.role],
              textAnchor: m.anchor,
              dx: m.anchor === "start" ? -2 : 2 - deltaW,
              fontWeight: 700,
            }),
          ];
          if (m.delta) {
            marks.push(
              Plot.text([m], {
                x: "x",
                frameAnchor: "top",
                dy,
                text: () => m.delta as string,
                fill: TONE_COLOR[tone],
                textAnchor: m.anchor,
                dx: m.anchor === "start" ? -2 + textW + CHAR_PX : 2,
                fontWeight: 400,
              }),
            );
          }
          return marks;
        }),
      ],
    });
    el.replaceChildren(chart);
    return () => chart.remove();
  }, [curve, decimals, width, meanChanges]);
  return (
    <figure className="curve" data-testid="curve">
      <figcaption className="name-col curve-label">{label}</figcaption>
      <div ref={ref} />
      {shape && (
        <>
          <LeagueShapeChart shape={shape} cat={cat} width={width} />
          <AgainstNullChart shape={shape} cat={cat} width={width} />
        </>
      )}
    </figure>
  );
}

export function CategoryCurves({ result }: { result: AnalysisResult }) {
  if (!result.curves.length) return null;
  const byKey = Object.fromEntries(result.categories.map((c) => [c.key, c]));
  // Every role drawn in any chart, in first-seen order: under focus a chart can drop its leader
  // when the opponent leads that category (011), so one chart's series isn't the whole legend.
  const series = result.curves
    .flatMap((c) => c.series)
    .filter((s, i, all) => all.findIndex((o) => o.role === s.role) === i);
  const originalOf: Partial<Record<Role, Role>> = { selected: "selected_original" };
  // Each "<Team> (before)" entry sits right after that team's own entry.
  const legend = series
    .filter((s) => !ORIGINAL_ROLES.includes(s.role))
    .flatMap((s) => {
      const orig = originalOf[s.role];
      const hasOrig = orig && series.some((o) => o.role === orig);
      return hasOrig ? [{ ...s }, { ...s, role: orig as Role, label: `${s.label} (before)` }] : [{ ...s }];
    });
  return (
    <section>
      <h3 className="section-divider">
        Category Breakdown <HelpButton topic="breakdown" />
      </h3>
      <div className="curve-legend">
        {legend.map((s) => (
          <span key={s.role} className="legend-item">
            <span
              className="swatch"
              style={{
                background: FILL[s.role],
                borderTop: `2px ${LEAGUE_ROLES.includes(s.role) || ORIGINAL_ROLES.includes(s.role) ? "dotted" : "solid"} ${STROKE[s.role]}`,
              }}
            />
            {s.role === "selected" || ORIGINAL_ROLES.includes(s.role)
              ? s.label
              : s.role === "league_average"
                ? "League Average"
                : s.role === "opponent" && result.focus
                  ? result.focus.opponent_name
                  : `${roleName(s.role)}`}
          </span>
        ))}
      </div>
      <div className="curve-grid">
        {result.curves.map((c) => (
          <CurveChart
            key={c.category}
            curve={c}
            label={byKey[c.category].label}
            decimals={byKey[c.category].decimals}
            meanChanges={result.changes?.curves[c.category]?.means}
            cat={byKey[c.category]}
            shape={result.league_shape?.find((s) => s.category === c.category)}
          />
        ))}
      </div>
    </section>
  );
}

function roleName(role: Role): string {
  return { leader: "League Leader", next_best: "Next Best", opponent: "Opponent" }[role as string] ?? role;
}
