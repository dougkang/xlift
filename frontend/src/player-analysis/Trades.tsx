import { useEffect, useState } from "react";
import { trades, type Trade, type TradesRequest, type TradesResult } from "../api/client";
import { formatXlift } from "../format";
import { HelpButton } from "../help/HelpButton";

const DEBOUNCE_MS = 250;

/** A category gain at one decimal, signed with a real minus (+2.7, 0.0, −1.3): nine of them share
 * the row with the two teams' gains, which keep xLift's two decimals. */
function oneDecimal(v: number | null): string {
  if (v === null || Number.isNaN(v)) return "–";
  const fixed = Math.abs(v).toFixed(1);
  if (fixed === "0.0") return "0.0";
  return `${v < 0 ? "−" : "+"}${fixed}`;
}

/** The Trade Finder (014): one row per other team with its most balanced win-win 1-for-1 trade,
 * in the server's order. The page only draws; the search and the pick are the server's. */
export function Trades({
  request,
  onTry,
}: {
  request: TradesRequest | null;
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

  const cats = result?.categories ?? [];
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
          <p className="scope-line trades-scope">
            For {result.team_name} · the fairest 1-for-1 trade with each team that helps both · weekly category wins
          </p>
          <div className="table-scroll">
            <table className="data trades-table">
              <thead>
                <tr>
                  <th className="col-header">Team</th>
                  <th className="col-header num">You</th>
                  <th className="col-header num">Them</th>
                  {/* Your gain in each category, so the trade's shape reads across the row. */}
                  {cats.map((c, i) => (
                    <th
                      key={c.key}
                      className={`col-header num cat-col${i === 0 ? " cat-first" : ""}`}
                      title={`Your weekly ${c.label} wins gained`}
                    >
                      {c.label}
                    </th>
                  ))}
                  <th aria-label="View Impact" />
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row) => {
                  const t = row.trade;
                  return (
                    <tr key={row.team_id} data-testid="trade-row" className={t ? undefined : "no-trade"}>
                      {/* The team, with the trade underneath: what you give and what you get. */}
                      <td className="trade-team">
                        <div className="name-col nowrap">
                          {row.team_name} <span className="sub">{row.manager}</span>
                        </div>
                        {t ? (
                          <div className="trade-sides">
                            <div className="nowrap">
                              <span className="col-header">Give</span> <TradePlayer p={t.give} />
                            </div>
                            <div className="nowrap">
                              <span className="col-header">Get</span> <TradePlayer p={t.get} />
                            </div>
                          </div>
                        ) : (
                          <div className="sub">No trade helps both teams.</div>
                        )}
                      </td>
                      {t && (
                        <>
                          <td className="num">{formatXlift(t.your_gain)}</td>
                          <td className="num">{formatXlift(t.their_gain)}</td>
                          {cats.map((c, i) => {
                            const gain = t.your_categories.find((g) => g.category === c.key)?.gain ?? null;
                            const shown = oneDecimal(gain);
                            return (
                              <td
                                key={c.key}
                                className={`num cat-col${i === 0 ? " cat-first" : ""}${shown.startsWith("+") ? " gain" : ""}`}
                              >
                                {shown}
                              </td>
                            );
                          })}
                          <td className="nowrap">
                            <button className="try-trade nowrap" onClick={() => onTry(t)}>
                              View Impact
                            </button>
                          </td>
                        </>
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
