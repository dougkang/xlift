import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { HelpContext, TopicId } from "./content";

interface HelpState {
  openId: TopicId | null;
  open: (id: TopicId) => void;
  close: () => void;
  ctx: HelpContext;
}

const Ctx = createContext<HelpState | null>(null);

/** Holds which help is open; opening one replaces any other, so at most one is open (FR-005). */
export function HelpProvider({ ctx, children }: { ctx: HelpContext; children: ReactNode }) {
  const [openId, setOpenId] = useState<TopicId | null>(null);
  const value = useMemo(() => ({ openId, open: setOpenId, close: () => setOpenId(null), ctx }), [openId, ctx]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useHelp(): HelpState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useHelp outside HelpProvider");
  return v;
}
