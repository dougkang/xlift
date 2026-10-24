import type { AnalysisResult } from "../api/client";
import { HelpButton } from "../help/HelpButton";

interface RosterProps {
  result: AnalysisResult;
  teamId: number;
  onDrop?: (playerId: number) => void;
}

export function Roster({ result, teamId, onDrop }: RosterProps) {
  const roster = result.rosters.find((r) => r.team_id === teamId);
  if (!roster) return null;
  const tactical = roster.players.some((p) => p.games_remaining !== null);
  return (
    <section>
      <h3 className="section-divider">
        Roster <HelpButton topic="roster" />
      </h3>
      <table className="data roster">
        <thead>
          <tr>
            {onDrop && <th aria-label="Drop" />}
            <th className="col-header">Player</th>
            <th className="col-header">Pos</th>
            {tactical && <th className="col-header num" title="Games left in the period">G</th>}
          </tr>
        </thead>
        <tbody>
          {roster.players.map((p) => (
            <tr key={p.player_id} className={[p.slot === "reserve" ? "muted" : "", p.moved ? "moved" : ""].join(" ").trim() || undefined}>
              {onDrop && (
                <td className="action-cell">
                  <button className="destructive row-action" aria-label={`Drop ${p.name}`} onClick={() => onDrop(p.player_id)}>
                    −
                  </button>
                </td>
              )}
              <td className="name-col nowrap">
                {p.name}
                {p.footnote_marker && <sup className="marker">{p.footnote_marker}</sup>}
                <span className="sub inline-sub">{p.nba_team ?? "–"}</span>
                {p.status !== "healthy" && (
                  <span className="status" title={p.slot === "reserve" ? "Reserve slot" : undefined}>
                    {" "}
                    {p.status}
                  </span>
                )}
              </td>
              <td>{p.positions.join(",") || "–"}</td>
              {tactical && <td className="num">{p.games_remaining ?? "–"}</td>}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="col-header open-slots">
        {roster.open_active_slots} open active slot{roster.open_active_slots === 1 ? "" : "s"}
      </div>
      <Footnotes result={result} />
    </section>
  );
}

export function Footnotes({ result }: { result: AnalysisResult }) {
  if (!result.footnotes.length) return null;
  const names = new Map(result.rosters.flatMap((r) => r.players.map((p) => [p.player_id, p.name] as const)));
  return (
    <ul className="footnotes">
      {result.footnotes.map((f) => (
        <li key={f.player_id}>
          {f.text} — {names.get(f.player_id) ?? f.player_id}
        </li>
      ))}
    </ul>
  );
}
