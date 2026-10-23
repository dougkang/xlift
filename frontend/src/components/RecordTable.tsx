import type { AnalysisResult, Schemas } from "../api/client";

type Counts = Schemas["RecordCounts"];

const RESULT_LABEL = { win: "W", loss: "L", tie: "T" } as const;

const wlt = (c: Counts) => `${c.wins}–${c.losses}–${c.ties}`;
const pct = (p: number) => `${Math.round(p * 100)}%`;

/** Projected record against each opponent, with a total row (values from the API). */
export function RecordTable({ result }: { result: AnalysisResult }) {
  const totals = result.matchup_totals;
  if (!result.matchups.length || !totals) return null;
  return (
    <section>
      <h3 className="section-divider">H2H</h3>
      <table className="data record-table">
        <thead>
          <tr>
            <th className="col-header">Opponent</th>
            <th className="col-header num nowrap">H2H</th>
            <th className="col-header num">Win</th>
            <th className="col-header num">Result</th>
          </tr>
        </thead>
        <tbody>
          {result.matchups.map((m) => (
            <tr key={m.opponent_id}>
              <td className="name-col">
                {m.opponent_name} <span className="sub">{m.opponent_manager}</span>
              </td>
              <td className="num nowrap">{wlt(m.category_record)}</td>
              <td className="num">{pct(m.matchup.win)}</td>
              <td className={`num result-${m.result}`}>{RESULT_LABEL[m.result]}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td className="name-col">Total</td>
            <td className="nowrap total-h2h" colSpan={2}>
              {wlt(totals.categories)}
            </td>
            <td className="num total-record">{wlt(totals.matchups)}</td>
          </tr>
        </tfoot>
      </table>
    </section>
  );
}
