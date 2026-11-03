import { ROUTE_HASH, type Route } from "../state/route";

const TOOLS: [Route, string][] = [
  ["impact", "Impact Analysis"],
  ["player-analysis", "Player Analysis"],
];

/** Plain-text tool nav above the masthead (009 contracts/ui.md "Navigation"). */
export function Nav({ current }: { current: Route }) {
  return (
    <nav className="tool-nav" aria-label="Tools">
      {TOOLS.map(([route, label]) => (
        <a
          key={route}
          href={ROUTE_HASH[route]}
          aria-current={route === current ? "page" : undefined}
          className={route === current ? "current" : undefined}
        >
          {label}
        </a>
      ))}
      {/* A plain page explaining xLift and dAB, served beside the app. */}
      <a href="./how-it-works.html">How it works</a>
    </nav>
  );
}
