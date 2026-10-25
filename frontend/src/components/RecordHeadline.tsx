import type { AnalysisResult, Schemas } from "../api/client";
import { Delta, Wins, WLTDelta } from "./Delta";
import { HelpButton } from "../help/HelpButton";

export function RecordHeadline({ result, pending = false }: { result: AnalysisResult; pending?: boolean }) {
  const { header, radar } = result;
  const rec = header.record;
  const opponents = radar ? radar.team_count - 1 : 0;
  const m = header.matchup;
  const ch = result.changes?.header;
  return (
    <header className={`record-headline${pending ? " pending" : ""}`}>
      <div className="team-block">
        {m && (
          // The week and the score so far, above the team (005 FR-014); the as-of date sits with
          // the other "last updated" dates under the intro.
          <div className="matchup-line" aria-label="Current matchup score">
            Week {m.week} · {shortDate(m.period_start)}–{shortDate(m.period_end)} ·{" "}
            {m.final ? "Final" : "Now"} {m.current.wins}–{m.current.losses}–{m.current.ties}
          </div>
        )}
        <div className="team">
          <h2 className="team-name">{header.team_name}</h2>
          <div className="manager">{header.manager}</div>
        </div>
        {m && (
          <h3 className="opponent-line">vs. {m.opponent_name}</h3>
        )}
      </div>
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

/** When the data was last loaded. Player Analysis doesn't use the matchup, so it can leave it out. */
export function DataLine({
  freshness: f,
  matchup = true,
}: {
  freshness: Schemas["Freshness"];
  matchup?: boolean;
}) {
  // Local calendar date (YYYY-MM-DD), like the roster and matchup dates; the stored time is UTC.
  const loaded = f.nba_data_loaded_at ? new Date(f.nba_data_loaded_at).toLocaleDateString("en-CA") : "never";
  return (
    <span className="data-line col-header">
      <span>Statistics last updated: {loaded}</span>
      <span>Rosters last updated: {f.roster_as_of ?? "–"}</span>
      {matchup && f.matchup_as_of && <span>Matchup last updated: {f.matchup_as_of}</span>}
    </span>
  );
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2026-11-18" → "Nov 18", without time-zone shifts. */
export function shortDate(iso: string): string {
  const [, mm, dd] = iso.split("-").map(Number);
  return `${MONTHS[mm - 1]} ${dd}`;
}
