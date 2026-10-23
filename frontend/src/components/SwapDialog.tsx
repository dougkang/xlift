import { useEffect, useState } from "react";
import { players, type PlayerRow, type ScenarioRequest, type Schemas } from "../api/client";

type TeamRoster = Schemas["TeamRoster"];

interface Props {
  target: PlayerRow;
  roster: TeamRoster;
  request: ScenarioRequest;
  onConfirm: (giveId: number) => void;
  onCancel: () => void;
}

/** "Give <team> one of:" — your roster (a trade) and/or a free agent, as the API allows. */
export function SwapDialog({ target, roster, request, onConfirm, onCancel }: Props) {
  const options = target.eligibility.swap_give_options;
  const [query, setQuery] = useState("");
  const [freeAgents, setFreeAgents] = useState<PlayerRow[]>([]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  useEffect(() => {
    if (!options.includes("free_agent")) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      players({ ...request, query, limit: 10, free_agents_only: true }, controller.signal)
        .then((p) => setFreeAgents(p.players))
        .catch(() => undefined);
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  return (
    <div className="swap-dialog" role="dialog" aria-label={`Swap for ${target.name}`}>
      <div className="swap-head">
        <span className="label">
          Get {target.name} — give {target.owner_label} one of:
        </span>
        <button onClick={onCancel}>Cancel</button>
      </div>
      {options.includes("roster") && (
        <>
          <div className="col-header">Your roster (trade)</div>
          <ul className="swap-list">
            {roster.players.map((p) => (
              <li key={p.player_id} className="swap-row">
                <button className="row-action" onClick={() => onConfirm(p.player_id)}>Give</button> {p.name}
                {p.slot === "reserve" && <span className="sub"> ({p.status})</span>}
              </li>
            ))}
          </ul>
        </>
      )}
      {options.includes("free_agent") && (
        <>
          <div className="col-header">A free agent</div>
          <input
            type="search"
            placeholder="Search free agents…"
            aria-label="Search free agents"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <ul className="swap-list">
            {freeAgents.map((p) => (
              <li key={p.player_id} className="swap-row">
                <button className="row-action" onClick={() => onConfirm(p.player_id)}>Give</button> {p.name}
                <span className="sub"> {p.nba_team}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
