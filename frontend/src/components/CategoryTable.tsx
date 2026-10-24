import type { AnalysisResult, Schemas } from "../api/client";
import { formatValue } from "../format";

type RankRow = Schemas["RankRow"];
type DifferenceRow = Schemas["DifferenceRow"];

export function CategoryTable({ result }: { result: AnalysisResult }) {
  const table = result.category_table;
  if (!table) return null;
  const byKey = Object.fromEntries(result.categories.map((c) => [c.key, c]));
  if (table.kind === "ranks") {
    return (
      <div className="category-table-wrap">
      <h3 className="section-divider">Per Category Ranking</h3>
      <table className="data category-table">
        <thead>
          <tr>
            <th className="col-header" aria-label="Category" />
            <th className="col-header num">Rank</th>
            <th className="col-header num">Avg</th>
            <th className="col-header num">League</th>
            <th className="col-header num">Leader</th>
            <th className="col-header num" title="Chance of beating a random league opponent in this category">
              Win %
            </th>
          </tr>
        </thead>
        <tbody>
          {(table.rows as RankRow[]).map((row) => {
            const cat = byKey[row.category];
            return (
              <tr key={row.category}>
                <td className="name-col">{cat.label}</td>
                <td className="num">{row.rank}</td>
                <td className="num">{formatValue(row.average, cat)}</td>
                <td className="num">{formatValue(row.league_average, cat)}</td>
                <td className="num" title={row.leader_name}>
                  {formatValue(row.leader_average, cat)}
                </td>
                <td className="num">{Math.round(row.win_rate * 100)}%</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    );
  }
  const opponent =
    result.matchups.find((m) => m.opponent_id === result.settings.opponent_id)?.opponent_name ?? "Opponent";
  return (
    <div className="category-table-wrap">
      <h3 className="section-divider">Per Category Difference</h3>
      <table className="data category-table">
        <thead>
          <tr>
            <th className="col-header" aria-label="Category" />
            <th className="col-header num">You</th>
            <th className="col-header num" title={opponent}>
              Opp
            </th>
            <th className="col-header num">Diff</th>
            <th className="col-header num">Win %</th>
          </tr>
        </thead>
        <tbody>
          {(table.rows as DifferenceRow[]).map((row) => {
            const cat = byKey[row.category];
            return (
              <tr key={row.category}>
                <td className="name-col">{cat.label}</td>
                <td className="num">{formatValue(row.selected_average, cat)}</td>
                <td className="num">{formatValue(row.opponent_average, cat)}</td>
                <td className={`num favors-${row.favors}`} data-favors={row.favors}>
                  {formatValue(row.difference, cat, true)}
                </td>
                <td className="num">{Math.round(row.win_probability * 100)}%</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
