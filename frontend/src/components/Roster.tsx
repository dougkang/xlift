import type { AnalysisResult } from "../api/client";
import { formatXlift } from "../format";
import type { TopicId } from "../help/content";
import { HelpButton } from "../help/HelpButton";

interface RosterProps {
  result: AnalysisResult;
  teamId: number;
  /** Without it the roster is read-only (the tactical opponent's roster, 005 FR-016). */
  onDrop?: (playerId: number) => void;
  title?: string;
  helpTopic?: TopicId;
}

export function Roster({ result, teamId, onDrop, title = "Roster", helpTopic = "roster" }: RosterProps) {
  const roster = result.rosters.find((r) => r.team_id === teamId);
  if (!roster) return null;
  const tactical = roster.players.some((p) => p.games_remaining !== null);
  return (
    <section>
      <h3 className="section-divider">
        {title} <HelpButton topic={helpTopic} />
      </h3>
      <table className="data roster">
        <thead>
          <tr>
            {onDrop && <th aria-label="Drop" />}
            <th className="col-header">Player</th>
            <th className="col-header">Pos</th>
            {tactical && <th className="col-header num" title="Games left in the period">G</th>}
            <th className="col-header num" title="Expected weekly category wins added for this team">
              xLift
            </th>
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
              <td className="num">{formatXlift(p.xlift)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="col-header open-slots">
        {roster.open_active_slots} open active slot{roster.open_active_slots === 1 ? "" : "s"}
      </div>
      <Footnotes result={result} playerIds={roster.players.map((p) => p.player_id)} />
    </section>
  );
}

/** Footnotes for the players in this roster (yours, or the opponent's in tactical). */
export function Footnotes({ result, playerIds }: { result: AnalysisResult; playerIds: number[] }) {
  const notes = result.footnotes.filter((f) => playerIds.includes(f.player_id));
  if (!notes.length) return null;
  const names = new Map(result.rosters.flatMap((r) => r.players.map((p) => [p.player_id, p.name] as const)));
  return (
    <ul className="footnotes">
      {notes.map((f) => (
        <li key={f.player_id}>
          {f.text} — {names.get(f.player_id) ?? f.player_id}
        </li>
      ))}
    </ul>
  );
}
