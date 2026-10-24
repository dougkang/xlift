# Phase 0 Research: Move Impact Highlighting

This feature builds on the 002 analysis pipeline (`ffmodel.tools.impact_analysis.analysis`).
Measurements are from the 002 validation run on the real 18-team league at 25,000 iterations:
about 0.5 s per analysis, warm.

## R1. Comparison basis and cost

**Decision**: when a request has moves, the server computes two analyses:
- the **original**: the same settings with no moves;
- the **current**: the same settings with the moves applied.

It then derives a `changes` block from the pair. With no moves, `changes` is `null` and no
original is computed (FR-003).

- **The original is cached:** it depends only on settings and data, never on moves. It is cached
  in-process, keyed by the same fields as the projection cache plus the selected team, opponent,
  seed and iterations. A session of moves pays for it once.
- **Untouched teams aren't re-simulated:** a team's samples depend only on its active player set,
  mode, seed and iteration count, because of the per-player random streams (002 research R2). The
  current analysis reuses the original's samples for every team whose active player set didn't
  change. Usually only the selected team and at most one trade partner are re-simulated, and the
  reused samples are bit-identical, which is what FR-002 / SC-003 require.

**Expected cost**:
- **First move:** about 0.5 s for the original plus the cost of the current, which reuses most
  samples.
- **Later moves:** under 0.5 s each.

That is within the 2 s SC-001 budget. It will be verified on the real league in the polish phase.

**Alternatives considered**:
- **Have the browser keep the previous result and diff it there.** Rejected for three reasons:
  - it breaks FR-017 (classification is domain logic, so it belongs on the server);
  - it compares against the previous step, not the original;
  - it gives wrong answers after a reload.
- **Re-run both analyses in full on every request.** About 1 s; it works, but it wastes half the
  budget. The cache and sample reuse are cheap.

## R2. Display precision and zero suppression (FR-005, FR-006)

**Decision**: the server rounds every change to the precision the page displays the value at.
When the rounded change is 0, the server returns `null`, so the page shows no marker and never
decides on its own.

| Value | Precision | Example |
|---|---|---|
| W/L/T counts, ranks | integer | `+2`, `−1` |
| Win %, chance to win | whole percentage points | `+13` |
| Area score (0–100) | integer | `+4` |
| Counting-category averages | 1 decimal | `+18.0`, `−0.4` |
| Ratio-category averages (FG%, FT%) | 3 decimals | `+.012` |

**Accompanying fix:** the page's average formatter currently shows 0 decimals for values ≥ 100.
It is aligned to the table above (always 1 decimal for counting averages), so the value and its
change are shown at the same precision.

## R3. Tone rules (FR-004): one function, one table

**Decision**: a single `tone(delta, better_when)` helper, where `better_when` is `"higher"`,
`"lower"`, or `"neutral"`. It returns `"better"`, `"worse"`, or `"neutral"`. Every field's rule is
declared next to the field:

| Field | better_when |
|---|---|
| W (matchups or H2H categories), win %, chance to win, area score | higher |
| L | lower |
| T | neutral |
| Rank | lower |
| Category average (yours) | the category's direction (`higher_is_better`) |
| Opp average (tactical) | the opposite of the category's direction |
| Diff (tactical) | the category's direction |
| League average, Leader average | neutral |
| Radar value (rank scale) | lower |
| Radar value (average and Win % scales) | higher |

**Result transitions** (H2H): the server returns `original_result` and `transition`, using an
order of L < T < W:

| Transition | When |
|---|---|
| `flip_better` | L → W |
| `flip_worse` | W → L |
| `better` | L → T or T → W |
| `worse` | W → T or T → L |
| `null` | No change |

## R4. Radar markers (FR-008): final

After trying spoke segments and then red/green layers, the user kept only the **gray dotted
outline of the original shape**. It's drawn for the selected team only, in both modes. The
opponent's original was dropped at the user's request. The default scale is **Win %**. `radar.original` is used;
`radar.tones` is still sent but unused.

## R5. Original distributions in the Category Breakdown (FR-012)

**Decision**: only the selected team's original distribution is added to the same
`density_curves` call as the current series, with the role `selected_original`, so they share one
x grid. Other teams' originals, including the tactical opponent's, are not drawn (revised at the
user's request).

- The originals are drawn first, as a light gray area (`#eee` fill, `#aaa` line), behind
  everything else.
- Original averages aren't drawn as lines. They appear only as the change on the current average
  label (`You 412.3 (+18.0)`), so the charts don't get more cluttered.

## R6. Colors and style amendment (FR-018)

**Decision**: per Constitution V, `docs/style.md` gains a "Change (before/after)" section:

- **Better:** `#5C8E4E`, the green from the style guide's qualitative palette.
- **Worse:** `#c00`, the existing warning red. Its permitted uses grow from two to three:
  destructive hover, status, and worse-change.
- **Neutral change:** `#555`, muted.
- **Original (before):** gray `#aaa` lines and `#eee` fills.
- **Deltas:** small text (`--header-size`), normal weight, right after the value. Bold is used
  only for result flips (L↔W).

## R7. Removed players

**Decision (user, option A)**: they are not shown in the roster. Listing them would add rows and
break the layout-stability rule (FR-019). Dropped players show up in the picker as free agents,
and traded players on their new team. No `removed_players` field is returned.
