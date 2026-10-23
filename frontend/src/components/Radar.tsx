import { scaleLinear } from "d3-scale";
import { curveLinearClosed, lineRadial } from "d3-shape";
import type { AnalysisResult } from "../api/client";

const SIZE = 320;
const R = 120;
const OTHER = ["var(--other-1)", "var(--other-2)", "var(--other-3)", "var(--other-4)"];

function strokeFor(emphasis: string, index: number): string {
  if (emphasis === "selected") return "var(--sel)";
  if (emphasis === "opponent") return "var(--opp)";
  return OTHER[index % OTHER.length];
}

export function Radar({ result }: { result: AnalysisResult }) {
  const radar = result.radar;
  if (!radar) return null;
  const cats = result.categories;
  const n = radar.team_count;
  // Rank 1 at the rim, rank n at the center.
  const radius = scaleLinear().domain([n, 1]).range([R * 0.12, R]);
  const angle = (i: number) => (2 * Math.PI * i) / cats.length;
  const line = lineRadial<number>()
    .angle((_, i) => angle(i))
    .radius((rank) => radius(rank))
    .curve(curveLinearClosed);
  const ordered = [...radar.series].sort((a, b) =>
    a.emphasis === "selected" ? 1 : b.emphasis === "selected" ? -1 : 0,
  );
  return (
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
          d={line(s.ranks) ?? undefined}
          fill={s.emphasis === "selected" ? "var(--sel-light)" : "var(--opp-light)"}
          fillOpacity={s.emphasis === "selected" ? 0.45 : 0.12}
          stroke={strokeFor(s.emphasis, idx)}
          strokeOpacity={s.emphasis === "other" ? 0.55 : 1}
          strokeWidth={s.emphasis === "selected" ? 2.5 : 1}
        >
          <title>{s.team_name}</title>
        </path>
      ))}
    </svg>
  );
}
