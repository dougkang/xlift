import { scaleLinear } from "d3-scale";
import { curveLinearClosed, lineRadial } from "d3-shape";
import type { AnalysisResult } from "../api/client";
import type { RadarScale } from "../state/scenario";

const SIZE = 320;
const R = 120;
/** The League Average uses the Category Breakdown's color and dotted average style. */
const LEAGUE_STROKE = { league_average: "var(--avg)" } as const;

const OTHER = ["var(--other-1)", "var(--other-2)", "var(--other-3)", "var(--other-4)"];

function strokeFor(emphasis: string, index: number): string {
  if (emphasis === "selected") return "var(--sel)";
  if (emphasis === "opponent") return "var(--opp)";
  return OTHER[index % OTHER.length];
}

export function Radar({ result, scale = "rank" }: { result: AnalysisResult; scale?: RadarScale }) {
  const radar = result.radar;
  if (!radar) return null;
  const pick = (s: { ranks: number[]; normalized: number[]; win_rate: number[] }) =>
    scale === "rank" ? s.ranks : scale === "average" ? s.normalized : s.win_rate;
  const cats = result.categories;
  const n = radar.team_count;
  // Rank scale: rank 1 at the rim, rank n at the center.
  // Average scale: the server's min-max normalized average, 1 (best) at the rim.
  // Win-rate scale: chance of beating a random league opponent, 100% at the rim, 0% at center.
  const radius =
    scale === "rank"
      ? scaleLinear().domain([n, 1]).range([R * 0.12, R])
      : scaleLinear().domain([0, 1]).range([R * 0.12, R]);
  const angle = (i: number) => (2 * Math.PI * i) / cats.length;
  const line = lineRadial<number>()
    .angle((_, i) => angle(i))
    .radius((rank) => radius(rank))
    .curve(curveLinearClosed);
  const ordered = [...radar.series].sort((a, b) =>
    a.emphasis === "selected" ? 1 : b.emphasis === "selected" ? -1 : 0,
  );
  const league = radar.league ?? [];
  return (
    <>
    <svg
      className="radar"
      viewBox={`${-SIZE / 2} ${-SIZE / 2} ${SIZE} ${SIZE}`}
      width={SIZE}
      height={SIZE}
      role="img"
      aria-label="Category rank radar"
    >
      {cats.map((c, i) => {
        const a = angle(i) - Math.PI / 2;
        return (
          <g key={c.key}>
            <line x1={0} y1={0} x2={R * Math.cos(a)} y2={R * Math.sin(a)} stroke="var(--rule)" />
            <text
              x={(R + 16) * Math.cos(a)}
              y={(R + 16) * Math.sin(a)}
              textAnchor="middle"
              dominantBaseline="middle"
              className="axis-label"
            >
              {c.label}
            </text>
          </g>
        );
      })}
      {ordered.map((s, idx) => (
        <path
          key={s.team_id}
          data-testid={`radar-${s.emphasis}`}
          d={line(pick(s)) ?? undefined}
          // The selected team is drawn last and filled solid in its border color: wherever we're
          // already better, other teams are hidden; only where they're better do they show.
          fill={s.emphasis === "selected" ? "var(--sel)" : "var(--opp-light)"}
          fillOpacity={s.emphasis === "selected" ? 1 : 0.15}
          stroke={strokeFor(s.emphasis, idx)}
          strokeOpacity={s.emphasis === "other" ? 0.55 : 1}
          strokeWidth={s.emphasis === "selected" ? 2.5 : 1}
        >
          <title>{s.team_name}</title>
        </path>
      ))}
      {/* League Average (strategic), dotted like the breakdown's average line. */}
      {league.map((l) => (
        <path
          key={l.role}
          data-testid={`radar-${l.role}`}
          d={line(pick(l)) ?? undefined}
          fill="none"
          stroke={LEAGUE_STROKE[l.role]}
          strokeWidth={1.5}
          strokeDasharray="2,3"
        >
          <title>{l.label}</title>
        </path>
      ))}
      {/* Original (before moves) shape as a gray dotted outline: the selected team only (003 FR-008). */}
      {result.changes?.radar.original.filter((o) => o.emphasis === "selected").map((o) => (
        <path
          key={`orig-${o.team_id}`}
          data-testid="radar-original"
          d={line(pick(o)) ?? undefined}
          fill="none"
          stroke="var(--before-line)"
          strokeWidth={1.5}
          strokeDasharray="4,3"
        >
          <title>Original (before moves)</title>
        </path>
      ))}
    </svg>
    {league.length > 0 && (
      <div className="curve-legend radar-legend">
        {league.map((l) => (
          <span key={l.role} className="legend-item">
            <span className="swatch line-swatch" style={{ borderTop: `2px dotted ${LEAGUE_STROKE[l.role]}` }} />
            {l.label}
          </span>
        ))}
      </div>
    )}
    </>
  );
}
