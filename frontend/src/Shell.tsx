import { useEffect } from "react";
import { ImpactAnalysis } from "./App";
import { Nav } from "./components/Nav";
import { PlayerAnalysis } from "./player-analysis/PlayerAnalysis";
import { useRoute } from "./state/route";
import { useScenario } from "./state/scenario";

/** Both tools under one state, so league, team, window and Fragility Penalty carry over (009
 * FR-004). Moves and mode belong to Impact Analysis; Player Analysis never changes them. */
export function Shell() {
  const [state, dispatch] = useScenario();
  const route = useRoute();
  useEffect(() => {
    document.title = route === "player-analysis" ? "Player Analysis" : "Impact Analysis";
  }, [route]);
  const nav = <Nav current={route} />;
  return route === "player-analysis" ? (
    <PlayerAnalysis state={state} dispatch={dispatch} nav={nav} />
  ) : (
    <ImpactAnalysis state={state} dispatch={dispatch} nav={nav} />
  );
}
