import { useEffect, useState } from "react";
import type { LeagueDetail, LeagueSummary } from "../api/client";
import type { Action, Fragility, Settings } from "../state/scenario";
import { HelpButton } from "../help/HelpButton";

interface Props {
  leagues: LeagueSummary[];
  league: LeagueDetail | null;
  settings: Settings;
  dispatch: (a: Action) => void;
  moveCount?: number;
}

const FRAGILITY: [Fragility, string][] = [
  ["none", "None"],
  ["last15", "Last 15"],
  ["dab", "dAB"],
  ["dab_tag", "dAB × tag"],
];

/** Last X games, Fragility Penalty, League, Team and Reset. Tactical's opponent and week come from the imported
 * matchup (005), so there are no vs or Week controls. */
export function Controls({ leagues, league, settings, dispatch, moveCount = 0 }: Props) {
  return (
    <div className="controls" role="group" aria-label="Analysis settings">
      <div className="controls-row">
        <label>
          <span className="col-header">Last</span>
          <WindowInput value={settings.window} onCommit={(n) => dispatch({ type: "setWindow", window: n })} />
          <span className="col-header">games</span>
        </label>
        <label>
          <span className="col-header">Fragility Penalty</span>
          <select
            value={settings.fragility}
            onChange={(e) => dispatch({ type: "setFragility", fragility: e.target.value as Fragility })}
          >
            {FRAGILITY.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
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
      </div>
      <div className="controls-row">
        <button onClick={() => dispatch({ type: "reset" })} disabled={moveCount === 0}>
          Reset{moveCount ? ` (${moveCount} move${moveCount === 1 ? "" : "s"})` : ""}
        </button>
      </div>
    </div>
  );
}

/** Strategic / Tactical toggle; sits in the masthead row, right-aligned. */
export const NO_MATCHUP = "This week's matchup hasn't been loaded yet";

/** Tactical needs the league's imported current matchup (005); without it the toggle is off. */
export function ModeToggle({
  settings,
  league,
  dispatch,
}: {
  settings: Settings;
  league: LeagueDetail | null;
  dispatch: (a: Action) => void;
}) {
  const noMatchup = league !== null && !league.current_matchup;
  return (
    <span className="mode-toggle" role="radiogroup" aria-label="Mode">
      {(["strategic", "tactical"] as const).map((m) => (
        <button
          key={m}
          className={`pill${settings.mode === m ? " active" : ""}`}
          role="radio"
          aria-checked={settings.mode === m}
          disabled={m === "tactical" && noMatchup}
          title={m === "tactical" && noMatchup ? NO_MATCHUP : undefined}
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
