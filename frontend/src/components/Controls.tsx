import { useEffect, useState } from "react";
import type { LeagueDetail, LeagueSummary } from "../api/client";
import type { Action, Settings } from "../state/scenario";

interface Props {
  leagues: LeagueSummary[];
  league: LeagueDetail | null;
  settings: Settings;
  dispatch: (a: Action) => void;
  tacticalAvailable?: boolean;
  moveCount?: number;
}

export function Controls({
  leagues,
  league,
  settings,
  dispatch,
  tacticalAvailable = false,
  moveCount = 0,
}: Props) {
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
        <WindowInput value={settings.window} onCommit={(n) => dispatch({ type: "setWindow", window: n })} />
        <span className="col-header">games</span>
      </label>
      <button onClick={() => dispatch({ type: "reset" })} disabled={moveCount === 0}>
        Reset{moveCount ? ` (${moveCount} move${moveCount === 1 ? "" : "s"})` : ""}
      </button>
    </div>
  );
}

/**
 * Free-form editing (including an empty field mid-edit); only valid values 1–82 are committed,
 * and leaving the field with an invalid draft restores the last committed value.
 */
export function WindowInput({ value, onCommit }: { value: number; onCommit: (n: number) => void }) {
  const [draft, setDraft] = useState(String(value));
  useEffect(() => setDraft(String(value)), [value]);
  const valid = (s: string) => /^\d+$/.test(s) && Number(s) >= 1 && Number(s) <= 82;
  return (
    <input
      type="text"
      inputMode="numeric"
      className="window-input"
      value={draft}
      aria-label="Games in window"
      aria-invalid={!valid(draft)}
      onChange={(e) => {
        const next = e.target.value.replace(/[^\d]/g, "").slice(0, 2);
        setDraft(next);
        if (valid(next) && Number(next) !== value) onCommit(Number(next));
      }}
      onBlur={() => {
        if (!valid(draft)) setDraft(String(value));
      }}
    />
  );
}
