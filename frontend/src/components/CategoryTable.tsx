import type { AnalysisResult, Schemas } from "../api/client";
import { formatActual, formatValue } from "../format";
import { WithDelta } from "./Delta";
import { HelpButton } from "../help/HelpButton";

type RankRow = Schemas["RankRow"];

/** Delta precision for an average: ratios at their 3 decimals, counts at 1 (003 R2). */
const avgDelta = (cat: Schemas["CategoryInfo"]) =>
  cat.decimals > 0 ? { decimals: cat.decimals, ratio: true } : { decimals: 1 };
type DifferenceRow = Schemas["DifferenceRow"];

/** A column header that fits: long team names are cut, with the full name on hover (011). */
export function shortName(name: string, max = 12): string {
  return name.length > max ? `${name.slice(0, max - 1)}…` : name;
}

export function CategoryTable({ result }: { result: AnalysisResult }) {
  const table = result.category_table;
  if (!table) return null;
  const byKey = Object.fromEntries(result.categories.map((c) => [c.key, c]));
  if (table.kind === "ranks") {
    return (
      <div className="category-table-wrap">
      <h3 className="section-divider">
        Per Category Ranking <HelpButton topic="categoryTable" />
      </h3>
      <table className="data category-table">
        <thead>
          <tr>
            <th className="col-header" aria-label="Category" />
            <th className="col-header num">Rank</th>
            <th className="col-header num">Avg</th>
            {/* Focused on an H2H opponent (011), the League column is that opponent's averages. */}
            {result.focus ? (
              <th className="col-header num nowrap" title={result.focus.opponent_name}>
                {shortName(result.focus.opponent_name)}
              </th>
            ) : (
              <th className="col-header num">League</th>
            )}
            <th className="col-header num">Leader</th>
            <th
              className="col-header num"
              title={
                result.focus
                  ? `Chance of beating ${result.focus.opponent_name} in this category`
                  : "Chance of beating a random league opponent in this category"
              }
            >
              Win %
            </th>
          </tr>
        </thead>
        <tbody>
          {(table.rows as RankRow[]).map((row) => {
            const cat = byKey[row.category];
            const ch = result.changes?.category_table[row.category];
            const avg = avgDelta(cat);
            return (
              <tr key={row.category}>
                <td className="name-col">{cat.label}</td>
                <td className="num">
                  <WithDelta change={ch?.rank}>{row.rank}</WithDelta>
                </td>
                <td className="num">
                  <WithDelta change={ch?.average} {...avg}>
                    {formatValue(row.average, cat)}
                  </WithDelta>
                </td>
                <td className="num">
                  <WithDelta change={ch?.league_average} {...avg}>
                    {formatValue(row.league_average, cat)}
                  </WithDelta>
                </td>
                <td className="num" title={row.leader_name}>
                  <WithDelta change={ch?.leader_average} {...avg}>
                    {formatValue(row.leader_average, cat)}
                  </WithDelta>
                </td>
                <td className="num">
                  <WithDelta change={ch?.win_rate} percent>
                    {Math.round(row.win_rate * 100)}%
                  </WithDelta>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    );
  }
  const opponent = result.header.matchup?.opponent_name ?? "Opponent";
  return (
    <div className="category-table-wrap">
      <h3 className="section-divider">
        Per Category Difference <HelpButton topic="categoryTable" />
      </h3>
      <table className="data category-table">
        <thead>
          <tr>
            <th className="col-header" aria-label="Category" />
            <th className="col-header num now-col" title="Week to date: you–opponent">
              Now
            </th>
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
            const ch = result.changes?.category_table[row.category];
            const avg = avgDelta(cat);
            return (
              <tr key={row.category}>
                <td className="name-col">{cat.label}</td>
                <td className="num now-col nowrap">
                  {formatActual(row.selected_actual, cat)}–{formatActual(row.opponent_actual, cat)}
                </td>
                <td className="num">
                  <WithDelta change={ch?.selected_average} {...avg}>
                    {formatValue(row.selected_average, cat)}
                  </WithDelta>
                </td>
                <td className="num">
                  <WithDelta change={ch?.opponent_average} {...avg}>
                    {formatValue(row.opponent_average, cat)}
                  </WithDelta>
                </td>
                <td className={`num favors-${row.favors}`} data-favors={row.favors}>
                  <WithDelta change={ch?.difference} {...avg}>
                    {formatValue(row.difference, cat, true)}
                  </WithDelta>
                </td>
                <td className="num">
                  <WithDelta change={ch?.win_probability} percent>
                    {Math.round(row.win_probability * 100)}%
                  </WithDelta>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
