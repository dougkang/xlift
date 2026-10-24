import type { AnalysisResult } from "../api/client";
import { Delta, Wins, WLTDelta } from "./Delta";
import { HelpButton } from "../help/HelpButton";

export function RecordHeadline({ result, pending = false }: { result: AnalysisResult; pending?: boolean }) {
  const { header, radar } = result;
  const rec = header.record;
  const opponents = radar ? radar.team_count - 1 : 0;
  const opponentName = result.matchups.find((m) => m.opponent_id === result.settings.opponent_id)?.opponent_name;
  const needsOpponent = result.warnings.some((w) => w.code === "OPPONENT_REQUIRED");
  const ch = result.changes?.header;
  return (
    <header className={`record-headline${pending ? " pending" : ""}`}>
      <div className="team-block">
        <div className="team">
          <h2 className="team-name">{header.team_name}</h2>
          <div className="manager">{header.manager}</div>
        </div>
        {rec?.unit === "categories" && opponentName && <h3 className="opponent-line">vs. {opponentName}</h3>}
      </div>
      {needsOpponent && <div className="score units">Choose an opponent</div>}
      {rec && rec.unit === "matchups" && (
        <div className="score">
          <div className="units" title={`W–L–T vs ${opponents} teams`}>Aggregated Record <HelpButton topic="headline" /></div>
          <div className="record nowrap" aria-label="Projected record">
            <Wins value={rec.wins} change={ch?.wins} />–{rec.losses}–{rec.ties}
          </div>
          <div className="delta-line">
            <WLTDelta change={ch} />
          </div>
        </div>
      )}
      {rec && rec.unit === "categories" && header.matchup_win_probability != null && (
        <div className="score">
          <div className="units">
            Chance to Win <HelpButton topic="headline" />
          </div>
          <div className="record nowrap" aria-label="Chance to win">
            {/* Colored like a changed W: green when the chance went up, red when down. */}
            <span className={ch?.chance_to_win ? `wins-${ch.chance_to_win.tone}` : undefined}>
              {Math.round(header.matchup_win_probability * 100)}%
            </span>
          </div>
          <div className="delta-line">
            <Delta change={ch?.chance_to_win} percent />
          </div>
        </div>
      )}
    </header>
  );
}

export function DataLine({ result }: { result: AnalysisResult }) {
  const f = result.freshness;
  const loaded = f.nba_data_loaded_at ? f.nba_data_loaded_at.slice(0, 16).replace("T", " ") : "never";
  return (
    <span className="data-line col-header">
      Statistics last updated: {loaded} · Rosters last updated: {f.roster_as_of ?? "–"}
    </span>
  );
}
