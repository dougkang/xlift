import type { AnalysisResult, Schemas } from "../api/client";
import { WithDelta, Wins, WLTWithDelta } from "./Delta";

type Counts = Schemas["RecordCounts"];

const RESULT_LABEL = { win: "W", loss: "L", tie: "T" } as const;

const pct = (p: number) => `${Math.round(p * 100)}%`;

/** Projected record against each opponent, with a total row (values from the API). */
type WLTChange = Schemas["WLTChange"];
type MatchupChange = Schemas["MatchupChange"];

/** W–L–T with its change in wins on the line below. */
function WLT({ counts, change }: { counts: Counts; change?: WLTChange | null }) {
  return (
    <WLTWithDelta change={change}>
      <Wins value={counts.wins} change={change?.wins} />–{counts.losses}–{counts.ties}
    </WLTWithDelta>
  );
}

const TRANSITION_CLASS = {
  flip_better: "flip-better",
  flip_worse: "flip-worse",
  better: "result-better",
  worse: "result-worse",
} as const;

function ResultCell({ result, change }: { result: "win" | "loss" | "tie"; change?: MatchupChange | null }) {
  const moved = change?.transition ? TRANSITION_CLASS[change.transition] : null;
  return (
    <td
      className={`num ${moved ?? `result-${result}`}`}
      title={change?.transition ? `was ${RESULT_LABEL[change.original_result]}` : undefined}
    >
      {RESULT_LABEL[result]}
    </td>
  );
}

export function RecordTable({ result }: { result: AnalysisResult }) {
  const changes = result.changes;
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
            <tr
              key={m.opponent_id}
              className={m.opponent_id === result.settings.opponent_id ? "opponent-row" : undefined}
            >
              <td className="name-col">
                {m.opponent_name} <span className="sub">{m.opponent_manager}</span>
              </td>
              <td className="num nowrap">
                <WLT counts={m.category_record} change={changes?.matchups[String(m.opponent_id)]?.category_record} />
              </td>
              <td className="num">
                <WithDelta change={changes?.matchups[String(m.opponent_id)]?.win} percent>
                  {pct(m.matchup.win)}
                </WithDelta>
              </td>
              <ResultCell result={m.result} change={changes?.matchups[String(m.opponent_id)]} />
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td className="name-col">Total</td>
            <td className="nowrap total-h2h" colSpan={2}>
              <WLT counts={totals.categories} change={changes?.matchup_totals.categories} />
            </td>
            <td className="num total-record nowrap">
              <WLT counts={totals.matchups} change={changes?.matchup_totals.matchups} />
            </td>
          </tr>
        </tfoot>
      </table>
    </section>
  );
}
