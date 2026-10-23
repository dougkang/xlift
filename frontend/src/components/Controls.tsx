import type { LeagueDetail, LeagueSummary } from "../api/client";
import type { Action, Settings } from "../state/scenario";

interface Props {
  leagues: LeagueSummary[];
  league: LeagueDetail | null;
  settings: Settings;
  dispatch: (a: Action) => void;
  tacticalAvailable?: boolean;
}

export function Controls({ leagues, league, settings, dispatch, tacticalAvailable = false }: Props) {
  return (
    <div className="controls" role="group" aria-label="Analysis settings">
      <label>
        <span className="col-header">League</span>
        <select
          value={settings.leagueId ?? ""}
          onChange={(e) => dispatch({ type: "setLeague", leagueId: Number(e.target.value) })}
        >
          <option value="" disabled>
            Choose…
          </option>
          {leagues.map((l) => (
            <option key={l.league_id} value={l.league_id}>
              {l.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className="col-header">Team</span>
        <select
          value={settings.teamId ?? ""}
          disabled={!league}
          onChange={(e) => dispatch({ type: "setTeam", teamId: Number(e.target.value) })}
        >
          <option value="" disabled>
            Choose…
          </option>
          {league?.teams.map((t) => (
            <option key={t.team_id} value={t.team_id}>
              {t.name} — {t.manager}
            </option>
          ))}
        </select>
      </label>
      <span className="mode-toggle" role="radiogroup" aria-label="Mode">
        {(["strategic", "tactical"] as const).map((m) => (
          <button
            key={m}
            className={`pill${settings.mode === m ? " active" : ""}`}
            role="radio"
            aria-checked={settings.mode === m}
            disabled={m === "tactical" && !tacticalAvailable}
            title={m === "tactical" && !tacticalAvailable ? "Tactical mode is not available yet" : undefined}
            onClick={() => dispatch({ type: "setMode", mode: m })}
          >
            {m === "strategic" ? "Strategic" : "Tactical"}
          </button>
        ))}
      </span>
      <label>
        <span className="col-header">Last</span>
        <input
          type="number"
          min={1}
          max={82}
          value={settings.window}
          aria-label="Games in window"
          onChange={(e) => {
            const n = Number(e.target.value);
            if (Number.isInteger(n) && n >= 1 && n <= 82) dispatch({ type: "setWindow", window: n });
          }}
        />
        <span className="col-header">games</span>
      </label>
    </div>
  );
}
