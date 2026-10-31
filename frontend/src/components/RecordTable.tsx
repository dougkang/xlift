import type { AnalysisResult, Schemas } from "../api/client";
import { Delta, WithDelta, Wins, WLTWithDelta } from "./Delta";
import { HelpButton } from "../help/HelpButton";
import { formatRecord } from "../format";

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
      title={change?.transition && change.original_result ? `was ${RESULT_LABEL[change.original_result]}` : undefined}
    >
      {RESULT_LABEL[result]}
    </td>
  );
}

type Expected = Schemas["ExpectedRecordModel"];

/** An expected category record with its change in expected wins below (010). */
function ExpectedWLT({ record, change }: { record: Expected; change?: Schemas["Change"] | null }) {
  return (
    <span className="with-delta">
      <span className={`nowrap${change ? ` wins-${change.tone}` : ""}`}>{formatRecord(record)}</span>
      <span className="delta-line">
        <Delta change={change} />
      </span>
    </span>
  );
}

/** Each-category standings (010): the expected category record per opponent; there is no
 * matchup result. */
function CategoryRecordTable({ result }: { result: AnalysisResult }) {
  const changes = result.changes;
  const total = result.matchup_totals?.expected;
  if (!total) return null;
  return (
    <section>
      <h3 className="section-divider">
        H2H <HelpButton topic="h2h" />
      </h3>
      <table className="data record-table">
        <thead>
          <tr>
            <th className="col-header">Opponent</th>
            <th className="col-header num nowrap">Record</th>
          </tr>
        </thead>
        <tbody>
          {result.matchups.map((m) =>
            m.expected_record ? (
              <tr
                key={m.opponent_id}
                className={m.opponent_id === result.settings.opponent_id ? "opponent-row" : undefined}
              >
                <td className="name-col">
                  {m.opponent_name} <span className="sub">{m.opponent_manager}</span>
                </td>
                <td className="num nowrap">
                  <ExpectedWLT
                    record={m.expected_record}
                    change={changes?.matchups[String(m.opponent_id)]?.expected_wins}
                  />
                </td>
              </tr>
            ) : null,
          )}
        </tbody>
        <tfoot>
          <tr>
            <td className="name-col">Total</td>
            <td className="num nowrap total-record">
              <ExpectedWLT record={total} change={changes?.matchup_totals?.expected_wins} />
            </td>
          </tr>
        </tfoot>
      </table>
    </section>
  );
}

export function RecordTable({ result }: { result: AnalysisResult }) {
  const changes = result.changes;
  const totals = result.matchup_totals;
  if (!result.matchups.length || !totals) return null;
  if (result.standings === "category") return <CategoryRecordTable result={result} />;
  return (
    <section>
      <h3 className="section-divider">
        H2H <HelpButton topic="h2h" />
      </h3>
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
              {m.result && <ResultCell result={m.result} change={changes?.matchups[String(m.opponent_id)]} />}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td className="name-col">Total</td>
            <td className="nowrap total-h2h" colSpan={2}>
              <WLT counts={totals.categories} change={changes?.matchup_totals?.categories} />
            </td>
            <td className="num total-record nowrap">
              {totals.matchups && <WLT counts={totals.matchups} change={changes?.matchup_totals?.matchups} />}
            </td>
          </tr>
        </tfoot>
      </table>
    </section>
  );
}
