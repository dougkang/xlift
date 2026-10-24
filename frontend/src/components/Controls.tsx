import { useEffect, useState } from "react";
import type { LeagueDetail, LeagueSummary } from "../api/client";
import type { Action, Settings } from "../state/scenario";
import { HelpButton } from "../help/HelpButton";

interface Props {
  leagues: LeagueSummary[];
  league: LeagueDetail | null;
  settings: Settings;
  dispatch: (a: Action) => void;
  moveCount?: number;
  /** Effective period from the last result, used to show the server's default week. */
  period?: { start: string | null; end: string | null };
}

export function Controls({
  leagues,
  league,
  settings,
  dispatch,
  moveCount = 0,
  period,
}: Props) {
  const tactical = settings.mode === "tactical";
  const start = settings.periodStart ?? period?.start ?? "";
  const end = settings.periodEnd ?? period?.end ?? "";
  return (
    <div className="controls" role="group" aria-label="Analysis settings">
      <div className="controls-row">
        <label>
          <span className="col-header">Last</span>
          <WindowInput value={settings.window} onCommit={(n) => dispatch({ type: "setWindow", window: n })} />
          <span className="col-header">games</span>
        </label>
        <HelpButton topic="settings" />
      </div>
      <div className="controls-row">
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
      </div>
      <div className="controls-row">
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
        {tactical && (
          <label>
            <span className="col-header">vs</span>
            <select
              aria-label="Opponent"
              value={settings.opponentId ?? ""}
              onChange={(e) =>
                dispatch({ type: "setOpponent", opponentId: e.target.value ? Number(e.target.value) : null })
              }
            >
              <option value="">Choose opponent…</option>
              {league?.teams
                .filter((t) => t.team_id !== settings.teamId)
                .map((t) => (
                  <option key={t.team_id} value={t.team_id}>
                    {t.name} — {t.manager}
                  </option>
                ))}
            </select>
          </label>
        )}
      </div>
      <div className="controls-row">
        {tactical && (
          <label>
            <span className="col-header">Week</span>
            <input
              type="date"
              aria-label="Period start"
              value={start}
              onChange={(e) => dispatch({ type: "setPeriod", start: e.target.value || null, end: end || null })}
            />
            <span className="col-header">to</span>
            <input
              type="date"
              aria-label="Period end"
              value={end}
              min={start || undefined}
              onChange={(e) => dispatch({ type: "setPeriod", start: start || null, end: e.target.value || null })}
            />
          </label>
        )}
        <button onClick={() => dispatch({ type: "reset" })} disabled={moveCount === 0}>
          Reset{moveCount ? ` (${moveCount} move${moveCount === 1 ? "" : "s"})` : ""}
        </button>
      </div>
    </div>
  );
}

/** Strategic / Tactical toggle; sits in the masthead row, right-aligned. */
export function ModeToggle({ settings, dispatch }: { settings: Settings; dispatch: (a: Action) => void }) {
  return (
    <span className="mode-toggle" role="radiogroup" aria-label="Mode">
      {(["strategic", "tactical"] as const).map((m) => (
        <button
          key={m}
          className={`pill${settings.mode === m ? " active" : ""}`}
          role="radio"
          aria-checked={settings.mode === m}
          onClick={() => dispatch({ type: "setMode", mode: m })}
        >
          {m === "strategic" ? "Strategic" : "Tactical"}
        </button>
      ))}
      <HelpButton topic="mode" />
    </span>
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
