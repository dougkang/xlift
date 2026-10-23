import type { AnalysisResult } from "../api/client";

export function RecordHeadline({ result, pending = false }: { result: AnalysisResult; pending?: boolean }) {
  const { header, radar } = result;
  const rec = header.record;
  const opponents = radar ? radar.team_count - 1 : 0;
  return (
    <header className={`record-headline${pending ? " pending" : ""}`}>
      <div className="team">
        <h2 className="team-name">{header.team_name}</h2>
        <div className="manager">{header.manager}</div>
      </div>
      {rec && (
        <div className="score">
          <div className="record" aria-label="Projected record">
            {rec.wins}–{rec.losses}–{rec.ties}
          </div>
          {rec.unit === "matchups" && <div className="units">vs {opponents} teams (W–L–T)</div>}
        </div>
      )}
    </header>
  );
}

export function DataLine({ result }: { result: AnalysisResult }) {
  const f = result.freshness;
  const loaded = f.nba_data_loaded_at ? f.nba_data_loaded_at.slice(0, 16).replace("T", " ") : "never";
  return (
    <div className="data-line col-header">
      Data: NBA {loaded} · Rosters {f.roster_as_of ?? "–"}
    </div>
  );
}
