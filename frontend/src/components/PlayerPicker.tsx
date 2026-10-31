import { useEffect, useRef, useState } from "react";
import { players, type PlayerPage, type PlayerRow, type ScenarioRequest } from "../api/client";
import { formatXlift } from "../format";

const PAGE = 50;
const DEBOUNCE_MS = 250;

const POSITIONS = ["G", "F", "C"] as const;
type Position = (typeof POSITIONS)[number];
type Owner = "fa" | number;

interface Props {
  request: ScenarioRequest;
  onAdd: (playerId: number) => void;
  onSwap: (player: PlayerRow) => void;
  /** The league's other fantasy teams, for the Team filter (013). */
  teams?: { team_id: number; name: string }[];
  /** The scoring format's categories, for Sort by (013). */
  categories?: { key: string; label: string }[];
}

const toggle = <T,>(list: T[], v: T) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

/** Everyone not on the selected team, in the server's order (xLift for the selected team, or
 * summed over the Sort by categories). Filtering, ranking and eligibility come from the API,
 * never computed here. */
export function PlayerPicker({ request, onAdd, onSwap, teams = [], categories = [] }: Props) {
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<PlayerPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [owners, setOwners] = useState<Owner[]>([]);
  const [sortBy, setSortBy] = useState<string[]>([]);
  // A team no longer offered (after a team change) drops out of the filter; a new league resets it.
  const offered = owners.filter((o) => o === "fa" || teams.some((t) => t.team_id === o));
  const sorted = sortBy.filter((k) => categories.some((c) => c.key === k));
  useEffect(() => {
    setPositions([]);
    setOwners([]);
    setSortBy([]);
  }, [request.league_id]);
  const filters = { positions, owners: offered, sort_categories: sorted };
  const key = JSON.stringify([request, filters]);

  useEffect(() => setOffset(0), [query, key]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      players({ ...request, ...filters, query, offset, limit: PAGE }, controller.signal)
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
  const sortLabel = sorted.map((k) => categories.find((c) => c.key === k)?.label ?? k).join("+");
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
      <div className="picker-filters">
        <div className="picker-filter" role="group" aria-label="Position">
          <span className="col-header">Pos</span>
          <span className="pills">
            {POSITIONS.map((p) => (
              <button
                key={p}
                className={`pill${positions.includes(p) ? " active" : ""}`}
                aria-pressed={positions.includes(p)}
                onClick={() => setPositions(toggle(positions, p))}
              >
                {p}
              </button>
            ))}
          </span>
        </div>
        <TeamFilter teams={teams} owners={offered} onChange={setOwners} />
        {categories.length > 0 && (
          <div className="picker-filter" role="group" aria-label="Sort by">
            <span className="col-header">Sort by</span>
            <span className="pills">
              {categories.map((c) => (
                <button
                  key={c.key}
                  className={`pill${sorted.includes(c.key) ? " active" : ""}`}
                  aria-pressed={sorted.includes(c.key)}
                  onClick={() => setSortBy(toggle(sorted, c.key))}
                >
                  {c.label}
                </button>
              ))}
            </span>
          </div>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {page && page.players.length === 0 && <p className="picker-empty">No players match.</p>}
      <table className="data picker-table">
        <thead>
          <tr>
            <th aria-label="Add" />
            <th className="col-header">Player</th>
            <th className="col-header">Pos</th>
            <th className="col-header">Team</th>
            {tactical && <th className="col-header num">G</th>}
            <th className="col-header num" title="Expected weekly category wins added for your team">
              xLift
            </th>
            {sortLabel && (
              <th className="col-header num nowrap" title={`xLift in ${sortLabel}: the order of this list`}>
                {sortLabel}
              </th>
            )}
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
                <td className="num">{formatXlift(p.xlift)}</td>
                {sortLabel && <td className="num sort-col">{formatXlift(p.sort_xlift ?? null)}</td>}
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

/** Team filter (013): a quiet button naming the choice, opening a checklist of Free agents and the
 * league's other teams. None checked means every team. */
function TeamFilter({
  teams,
  owners,
  onChange,
}: {
  teams: { team_id: number; name: string }[];
  owners: Owner[];
  onChange: (owners: Owner[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);
  const choices: [Owner, string][] = [["fa", "Free agents"], ...teams.map((t): [Owner, string] => [t.team_id, t.name])];
  const summary =
    owners.length === 0
      ? "All"
      : owners.length === 1
        ? choices.find(([o]) => o === owners[0])?.[1]
        : `${owners.length} picked`;
  return (
    <div className="picker-filter team-filter" ref={ref}>
      <span className="col-header">Team</span>
      <span className="pills">
        <button className="select-button" aria-haspopup="true" aria-expanded={open} aria-label="Team" onClick={() => setOpen(!open)}>
          {summary}
        </button>
      </span>
      {open && (
        <div className="team-filter-menu" role="group" aria-label="Teams">
          {choices.map(([o, label]) => (
            <label key={String(o)}>
              <input type="checkbox" checked={owners.includes(o)} onChange={() => onChange(toggle(owners, o))} /> {label}
            </label>
          ))}
          {owners.length > 0 && (
            <button className="clear" onClick={() => onChange([])}>
              All teams
            </button>
          )}
        </div>
      )}
    </div>
  );
}
