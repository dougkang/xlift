import { useEffect, useState } from "react";

/** The two tools (009 research R8): hash routes, so no router and no server fallback. */
export type Route = "impact" | "player-analysis";

export const ROUTE_HASH: Record<Route, string> = { impact: "#/", "player-analysis": "#/player-analysis" };

export function parseRoute(hash: string): Route {
  return hash === ROUTE_HASH["player-analysis"] ? "player-analysis" : "impact";
}

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
