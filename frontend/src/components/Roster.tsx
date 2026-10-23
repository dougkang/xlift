import type { AnalysisResult } from "../api/client";

export function Roster({ result, teamId }: { result: AnalysisResult; teamId: number }) {
  const roster = result.rosters.find((r) => r.team_id === teamId);
  if (!roster) return null;
  return (
    <section>
      <h3 className="section-divider">Roster</h3>
      <table className="data roster">
        <thead>
          <tr>
            <th className="col-header">Player</th>
            <th className="col-header">NBA</th>
            <th className="col-header">Pos</th>
            <th className="col-header">Status</th>
          </tr>
        </thead>
        <tbody>
          {roster.players.map((p) => (
            <tr key={p.player_id} className={[p.slot === "reserve" ? "muted" : "", p.moved ? "moved" : ""].join(" ").trim() || undefined}>
              <td className="name-col">
                {p.name}
                {p.footnote_marker && <sup className="marker">{p.footnote_marker}</sup>}
              </td>
              <td>{p.nba_team ?? "–"}</td>
              <td>{p.positions.join(",") || "–"}</td>
              <td>{p.slot === "reserve" ? `${p.status} (reserve)` : p.status === "healthy" ? "" : p.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
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
