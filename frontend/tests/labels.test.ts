import { describe, expect, it } from "vitest";
import { placeLabels } from "../src/components/CategoryCurves";

describe("placeLabels", () => {
  it("keeps far-apart labels on one row", () => {
    const placed = placeLabels(
      [
        { x: 0, role: "selected", text: "You 1.0" },
        { x: 100, role: "league_average", text: "League 9.0" },
      ],
      [0, 100],
    );
    expect(placed.map((p) => p.row)).toEqual([0, 0]);
    expect(placed.map((p) => p.anchor)).toEqual(["start", "end"]);
  });

  it("jitters colliding labels onto separate rows", () => {
    const placed = placeLabels(
      [
        { x: 50, role: "selected", text: "You .471" },
        { x: 51, role: "leader", text: "Leader .480" },
        { x: 52, role: "league_average", text: "League .465" },
      ],
      [0, 100],
    );
    expect(new Set(placed.map((p) => p.row)).size).toBe(3);
  });
});
