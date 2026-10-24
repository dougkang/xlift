import type { ReactNode } from "react";
import type { Schemas } from "../api/client";

export type Change = Schemas["Change"];

/** Signed change marker (003 contracts/ui.md). Renders nothing for a null change. */
export function Delta({
  change,
  decimals = 0,
  ratio = false,
  percent = false,
}: {
  change: Change | null | undefined;
  decimals?: number;
  ratio?: boolean;
  /** Percentage-point changes (win %, chance to win) show a % sign, e.g. "+13%". */
  percent?: boolean;
}) {
  if (!change) return null;
  const sign = change.delta > 0 ? "+" : "−";
  let text = Math.abs(change.delta).toFixed(decimals);
  if (ratio) text = text.replace(/^0(?=\.)/, "");
  if (percent) text += "%";
  const word = change.delta > 0 ? "up" : "down";
  return (
    <span className={`delta delta-${change.tone}`} aria-label={`${word} ${text}, ${change.tone}`}>
      {sign}
      {text}
    </span>
  );
}

/** A value with its change on the line below. The second line is always reserved, so the
 * layout doesn't shift when changes appear or disappear (003 FR-019). */
export function WithDelta({ children, ...delta }: { children: ReactNode } & Parameters<typeof Delta>[0]) {
  return (
    <span className="with-delta">
      <span className="nowrap">{children}</span>
      <span className="delta-line">
        <Delta {...delta} />
      </span>
    </span>
  );
}

type WLT = { wins?: Change | null; losses?: Change | null; ties?: Change | null } | null | undefined;

/** Record change: only the change in wins (e.g. "+2"), green when wins go up. */
export function WLTDelta({ change }: { change: WLT }) {
  return <Delta change={change?.wins} />;
}

/** The wins count, colored by its change: green when wins went up, red when down. */
export function Wins({ value, change }: { value: number; change: Change | null | undefined }) {
  return <span className={change ? `wins-${change.tone}` : undefined}>{value}</span>;
}

/** A W–L–T record with its change in wins below, space reserved. */
export function WLTWithDelta({ children, change }: { children: ReactNode; change: WLT }) {
  return (
    <span className="with-delta">
      <span className="nowrap">{children}</span>
      <span className="delta-line">
        <WLTDelta change={change} />
      </span>
    </span>
  );
}
