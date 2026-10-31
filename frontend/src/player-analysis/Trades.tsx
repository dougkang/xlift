import { useEffect, useState } from "react";
import { trades, type Trade, type TradesRequest, type TradesResult } from "../api/client";
import { formatXlift } from "../format";
import { HelpButton } from "../help/HelpButton";

const DEBOUNCE_MS = 250;

/** The Trade Finder (014): one row per other team with its most balanced win-win 1-for-1 trade,
 * in the server's order. The page only draws; the search and the pick are the server's. */
export function Trades({
  request,
  movesCount,
  onTry,
}: {
  request: TradesRequest | null;
  movesCount: number;
  onTry: (trade: Trade) => void;
}) {
  const [result, setResult] = useState<TradesResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const key = JSON.stringify(request);

  useEffect(() => {
    if (!request) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setPending(true);
      trades(request, controller.signal)
        .then((r) => {
          setResult(r);
          setError(null);
        })
        .catch((e: unknown) => {
          if (!controller.signal.aborted) setError(e instanceof Error ? e.message : String(e));
        })
        .finally(() => {
          if (!controller.signal.aborted) setPending(false);
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const label = (key: string) => result?.categories.find((c) => c.key === key)?.label ?? key;
  const tryLabel = movesCount > 0 ? "Try it (replaces your moves)" : "Try it";
  return (
    <section className={pending ? "pending" : undefined}>
      <h3 className="section-divider">
        Trades <HelpButton topic="trades" />
      </h3>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {result?.warnings.map((w) => (
        <p key={w.code} className="error" role="status">
          {w.message}
        </p>
      ))}
      {result && result.rows.length > 0 && (
        <>
          <p className="scope-line">
            For {result.team_name} · the fairest 1-for-1 trade with each team that helps both · weekly category wins
          </p>
          <div className="table-scroll">
            <table className="data trades-table">
              <thead>
                <tr>
                  <th className="col-header">Team</th>
                  <th className="col-header">You give</th>
                  <th className="col-header">You get</th>
                  <th className="col-header num">You</th>
                  <th className="col-header num">Them</th>
                  <th className="col-header">Why</th>
                  <th aria-label="Try it" />
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row) => {
                  const t = row.trade;
                  return (
                    <tr key={row.team_id} data-testid="trade-row" className={t ? undefined : "no-trade"}>
                      <td className="name-col nowrap">
                        {row.team_name} <span className="sub">{row.manager}</span>
                      </td>
                      {t ? (
                        <>
                          <td className="nowrap">
                            <TradePlayer p={t.give} />
                          </td>
                          <td className="nowrap">
                            <TradePlayer p={t.get} />
                          </td>
                          <td className="num">{formatXlift(t.your_gain)}</td>
                          <td className="num">{formatXlift(t.their_gain)}</td>
                          <td className="why">
                            {t.your_categories.map((c) => (
                              <span key={c.category} className={c.gain < 0 ? "loss" : undefined}>
                                {c.gain > 0 ? "+" : "−"}
                                {label(c.category)}
                              </span>
                            ))}
                          </td>
                          <td>
                            <button className="try-trade" onClick={() => onTry(t)}>
                              {tryLabel}
                            </button>
                          </td>
                        </>
                      ) : (
                        <td colSpan={6} className="sub">
                          No trade helps both teams.
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

function TradePlayer({ p }: { p: Trade["give"] }) {
  return (
    <>
      <span className="player-name">{p.name}</span> <span className="sub">{p.nba_team ?? "–"}</span>
      {p.status !== "healthy" && <span className="status"> {p.status}</span>}
    </>
  );
}
