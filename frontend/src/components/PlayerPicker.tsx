import { useEffect, useState } from "react";
import { players, type PlayerPage, type PlayerRow, type ScenarioRequest } from "../api/client";

const PAGE = 50;
const DEBOUNCE_MS = 250;

interface Props {
  request: ScenarioRequest;
  onAdd: (playerId: number) => void;
  onSwap: (player: PlayerRow) => void;
}

/** Everyone not on the selected team. Eligibility comes from the API, never computed here. */
export function PlayerPicker({ request, onAdd, onSwap }: Props) {
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<PlayerPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const key = JSON.stringify(request);

  useEffect(() => setOffset(0), [query, key]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      players({ ...request, query, offset, limit: PAGE }, controller.signal)
        .then((p) => {
          setPage(p);
          setError(null);
        })
        .catch((e: Error) => {
          if (!controller.signal.aborted) setError(e.message);
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, query, offset]);

  const tactical = request.mode === "tactical";
  return (
    <div className="picker">
      <input
        type="search"
        className="picker-search"
        placeholder="Search players…"
        aria-label="Search players"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {error && <p className="error">{error}</p>}
      <table className="data picker-table">
        <thead>
          <tr>
            <th aria-label="Add" />
            <th className="col-header">Player</th>
            <th className="col-header">Pos</th>
            <th className="col-header">Team</th>
            {tactical && <th className="col-header num">G</th>}
          </tr>
        </thead>
        <tbody>
          {page?.players.map((p) => {
            const e = p.eligibility;
            const swappable = !e.can_add && e.swap_give_options.length > 0;
            const disabled = !e.can_add && !swappable;
            return (
              <tr key={p.player_id}>
                <td className="action-cell">
                  <button
                    className="row-action"
                    aria-label={`Add ${p.name}`}
                    title={disabled || swappable ? (e.add_blocked_reason ?? undefined) : undefined}
                    disabled={disabled}
                    onClick={() => (e.can_add ? onAdd(p.player_id) : onSwap(p))}
                  >
                    +
                  </button>
                </td>
                <td className="name-col nowrap">
                  {p.name}
                  {p.footnote && <sup className="marker" title={p.footnote}>*</sup>}
                  <span className="sub inline-sub">{p.nba_team ?? "–"}</span>
                  {p.status !== "healthy" && <span className="status"> {p.status}</span>}
                </td>
                <td>{p.positions.join(",") || "–"}</td>
                <td className={p.owner_team_id === null ? "fa" : "sub"}>{p.owner_label}</td>
                {tactical && <td className="num">{p.games_remaining ?? "–"}</td>}
              </tr>
            );
          })}
        </tbody>
      </table>
      {page && page.total > PAGE && (
        <div className="pager">
          <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>
            ‹ Prev
          </button>
          <span className="col-header">
            {offset + 1}–{Math.min(offset + PAGE, page.total)} of {page.total}
          </span>
          <button disabled={offset + PAGE >= page.total} onClick={() => setOffset(offset + PAGE)}>
            Next ›
          </button>
        </div>
      )}
    </div>
  );
}
