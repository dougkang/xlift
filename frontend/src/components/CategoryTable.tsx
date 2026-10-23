import type { AnalysisResult, Schemas } from "../api/client";
import { formatValue } from "../format";

type RankRow = Schemas["RankRow"];

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
            <th className="col-header" aria-label="Leader team" />
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
                <td className="num">{formatValue(row.leader_average, cat)}</td>
                <td className="leader-team">{row.leader_name}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    );
  }
  return null;
}
