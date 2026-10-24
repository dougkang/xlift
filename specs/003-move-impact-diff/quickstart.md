# Quickstart & Validation: Move Impact Highlighting

The prerequisites are the same as for 002 ([002 quickstart](../002-impact-analysis/quickstart.md)):
data loaded, `ffm serve` running, and the frontend built.

## A. Offline checks (CI)

```bash
cd backend && uv run pytest && uv run lint-imports
cd ../frontend && npm test && npm run build
```

| Check | Proves |
|---|---|
| No moves → `changes` is null; with moves → `changes` is present | FR-003, SC-002 |
| A free-agent add touches only the selected team: every untouched team's samples are reused (bit-identical), and their changes are null | FR-002, SC-003 |
| Tone table (research R3), including the inverted cases: L, rank, TO average, Opp average | FR-004, SC-005 |
| Zero suppression at display precision | FR-006 |
| Transition rules: L→W `flip_better`, W→L `flip_worse`, L→T / T→W `better`, W→T / T→L `worse` | FR-013 |
| A trade with the tactical opponent: the opponent's original radar outline and `opponent_average` changes appear | FR-008, FR-011 |
| The original is cached: the second request with different moves does not recompute it | research R1 |
| Frontend: each of the 9 inventory places renders Deltas and tones from a recorded fixture, and nothing renders when `changes` is null | SC-002, SC-004 |

## B. Real league (manual)

```bash
cd backend && uv run pytest -m slow     # includes a with-moves timing case (SC-001)
```

Expected: with moves, an analysis still takes under 2 s.

## C. In the browser

1. Pick a team. There should be no change markers anywhere.
2. Drop a strong player. Check that:
   - the headline W shows red `−n` (or L shows red `+n`);
   - the radar shows red spoke segments and the gray original outline;
   - the curves show grayed originals;
   - the dropped player leaves the roster, and the layout doesn't change (option A).
3. Add a free agent. The markers update to show the net change against the original.
4. Make a trade. Opponent rows in H2H that flip show bold green W / bold red L.
5. Switch radar scales and change the window. The markers keep comparing against the original
   under the same settings.
6. Switch to Tactical, choose an opponent, and check the chance-to-win delta and the
   difference-table deltas.
7. Press Reset. Every marker disappears, and **nothing on the page moves** (FR-019). At 1,100 px
   and at 900 px, check that no value, cell, label or headline wraps when the markers appear.

## Validation log

**2026-10-23**, real `ccsv-2026` league, 25,000 iterations:

- **A. Offline checks:** 272 backend tests and 25 frontend tests pass. That includes 24 tests of the
  change and tone rules, 11 integration tests of the `changes` block, the 9-place change markers,
  and the layout-stability test (every marker sits in a no-wrap container). Lint is clean, the
  import-linter contracts hold, and the frontend builds.
- **B. `pytest -m slow -k with_moves`** (SC-001): analyses with moves take 0.89 s in strategic mode
  and 0.82 s in tactical mode on the first move, when the original is computed. Later moves, with
  the original cached, take 0.27 s and 0.26 s.
- **Untouched teams** (SC-003): a free-agent add re-simulates only the selected team. Every other
  team's samples are the original's own objects.
- **C. Browser:** the page is served by `ffm serve` with the new build. The visual SC-007 check
  (no wraps at 1,100 px and 900 px, nothing moves on Reset) is left to the user's review.
