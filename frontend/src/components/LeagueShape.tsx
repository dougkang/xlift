import { scaleLinear } from "d3-scale";
import type { Schemas } from "../api/client";
import { formatValue } from "../format";

type Shape = Schemas["CategoryShape"];
type Category = Schemas["CategoryInfo"];

const HEIGHT = 90;
const PAD = { top: 8, right: 6, bottom: 14, left: 6 };

/** x positions for places 1…n across the chart's inner width (shared by both charts). */
function placeScale(n: number, width: number) {
  return scaleLinear()
    .domain([1, Math.max(n, 2)])
    .range([PAD.left + 4, width - PAD.right - 4]);
}

function PlaceAxis({ n, width }: { n: number; width: number }) {
  const x = placeScale(n, width);
  return (
    <g className="shape-axis">
      <text x={x(1)} y={HEIGHT - 3} textAnchor="middle">
        1
      </text>
      <text x={x(n)} y={HEIGHT - 3} textAnchor="middle">
        {n}
      </text>
    </g>
  );
}

/**
 * League shape (008): every team's projected value by place, the selected team marked. Places,
 * ranks and values come from the API; nothing is ranked here.
 */
export function LeagueShapeChart({ shape, cat, width }: { shape: Shape; cat: Category; width: number }) {
  const teams = shape.teams;
  if (!teams.length) return null;
  const values = teams.map((t) => t.value).concat(shape.before ? [shape.before.value] : []);
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || Math.abs(hi) || 1;
  const x = placeScale(teams.length, width);
  // Higher values plot higher (for TO, the values rise with place, so the line slopes up).
  const y = scaleLinear()
    .domain([lo - span * 0.08, hi + span * 0.08])
    .range([HEIGHT - PAD.bottom, PAD.top]);
  const ordered = [...teams].sort((a, b) => Number(a.selected) - Number(b.selected));
  return (
    <figure className="shape-chart">
      <svg
        data-testid="league-shape"
        role="img"
        aria-label={`League shape: ${cat.label}`}
        width={width}
        height={HEIGHT}
      >
        <polyline
          fill="none"
          stroke="var(--shape-line)"
          strokeWidth={1}
          points={teams.map((t) => `${x(t.place)},${y(t.value)}`).join(" ")}
        />
        {shape.before && (
          <circle
            data-testid="shape-before"
            cx={x(shape.before.place)}
            cy={y(shape.before.value)}
            r={4}
            fill="none"
            stroke="var(--before-line)"
            strokeWidth={1.5}
          >
            <title>{`before your moves · rank ${shape.before.rank} · ${formatValue(shape.before.value, cat)}`}</title>
          </circle>
        )}
        {ordered.map((t) => (
          <circle
            key={t.team_id}
            data-team={t.team_id}
            data-selected={t.selected ? "true" : undefined}
            cx={x(t.place)}
            cy={y(t.value)}
            r={t.selected ? 4 : 2.5}
            fill={t.selected ? "var(--sel)" : "var(--shape-team)"}
          >
            <title>{`${t.team_name} · rank ${t.rank} · ${formatValue(t.value, cat)}`}</title>
          </circle>
        ))}
        <PlaceAxis n={teams.length} width={width} />
      </svg>
    </figure>
  );
}

const MARK_FILL = { climb: "var(--climb)", cushion: "var(--cushion)" } as const;

/**
 * Against null (008): the gap to reach each place, against a normal league's gap (dotted). The
 * selected team's climb and cushion are marked by the API.
 */
export function AgainstNullChart({ shape, cat, width }: { shape: Shape; cat: Category; width: number }) {
  const gaps = shape.gaps;
  if (!gaps.length) return null;
  const n = shape.teams.length;
  const x = placeScale(n, width);
  const top = Math.max(...gaps.map((g) => Math.max(g.gap, g.null_gap))) || 1;
  const y = scaleLinear()
    .domain([0, top * 1.08])
    .range([HEIGHT - PAD.bottom, PAD.top]);
  // Each bar sits between places r and r + 1.
  const step = (x(2) - x(1)) * 0.8;
  const mid = (r: number) => (x(r) + x(r + 1)) / 2;
  return (
    <figure className="shape-chart">
      <svg data-testid="against-null" role="img" aria-label={`Against null: ${cat.label}`} width={width} height={HEIGHT}>
        {gaps.map((g) => (
          <rect
            key={g.to_place}
            data-mark={g.mark ?? undefined}
            x={mid(g.to_place) - step / 2}
            y={y(g.gap)}
            width={step}
            height={Math.max(0, y(0) - y(g.gap))}
            fill={g.mark ? MARK_FILL[g.mark] : "var(--gap)"}
          >
            <title>{`to place ${g.to_place} · gap ${formatValue(g.gap, cat)} · normal gap ${formatValue(g.null_gap, cat)}`}</title>
          </rect>
        ))}
        <polyline
          data-testid="null-line"
          fill="none"
          stroke="var(--avg)"
          strokeWidth={1.5}
          strokeDasharray="2,3"
          points={gaps.map((g) => `${mid(g.to_place)},${y(g.null_gap)}`).join(" ")}
        />
        <PlaceAxis n={n} width={width} />
      </svg>
    </figure>
  );
}
