# Feature Specification: Move Impact Highlighting

**Feature Branch**: `003-move-impact-diff`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "visually display impact of add/drop/trades of players in the impact analysis tool. differences in the radar should be clearly denoted with red or green. the category breakdown should show a grayed out distribution representing the original distribution. changes in numbers should be denoted with a small +xx or -xx. where possible. for W-L-T records, W should be green if increased, red if decrased. the inverse should apply for losses. for results, a W that becomes an L should be bolded and red. an L that changes to a W should be bolded and green. take stock of every place where this change needs to happen."

## Overview

Impact Analysis (feature 002) recomputes everything after a roster move, but you can only see
the new state. To judge a move you have to remember the old numbers. This feature shows **what
changed**:
- every projected number on the page is compared with the **original**, the loaded rosters with
  no moves;
- every difference is marked consistently: a small signed change (`+3`, `−0.8`, `+.012`), green
  when it helps your team and red when it hurts.

When no moves have been made, nothing is marked and the page looks exactly as it does today.

### Inventory: every place that shows change

| # | Place on the page | What is compared | How change is shown |
|---|---|---|---|
| 1 | **Headline, strategic**: Aggregated Record | W, L, T matchups | Each count gets a small delta. W is green when up and red when down; L is red when up and green when down; T is neutral gray |
| 2 | **Headline, tactical**: Chance to Win | Matchup win % | Delta in percentage points (`+12`), green or red |
| 3 | **Radar** | The selected team's shape | The original shape as a gray dotted outline over the current one. No red/green fills. The default scale is Win % |
| 4 | **Radar scale tabs** | Area score (0–100) | Small delta beside each tab's score, green or red |
| 5 | **Per Category Ranking** (strategic) | Rank, Avg, League, Leader, Win % | Delta on each changed cell. For Rank, a smaller number is an improvement, so −2 is green. Avg and Win % follow the category direction (fewer TO is green). League and Leader deltas are neutral gray, since they describe the league rather than your team |
| 6 | **Per Category Difference** (tactical) | You, Opp, Diff, Win % | Delta on each changed cell, colored by whether it helps your team. Opp is colored inversely: the opponent getting worse is green |
| 7 | **Category Breakdown curves** | Your distribution in each category (and the opponent's, in tactical) | The original distribution is drawn grayed out behind the current one. The average label gets a delta, e.g. `You 412.3 (+18.0)`, green or red |
| 8 | **H2H table**, each opponent row | H2H W–L–T, Win %, Result | The H2H counts follow rule 1. Win % gets a delta. The Result follows the transition rules below |
| 9 | **H2H table**, Total row | Summed H2H W–L–T, matchup W–L–T | Same as rule 1 |

### Result transitions (H2H table)

| Original → Now | Display |
|---|---|
| L → W | **Bold green W** |
| W → L | **Bold red L** |
| L → T, T → W | Green, not bold (better, but not a flip) |
| W → T, T → L | Red, not bold (worse, but not a flip) |
| Unchanged | Normal (as today) |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the net effect of my moves at a glance (Priority: P1)

As a league member, after dropping, adding, or trading players I immediately see how my
headline numbers changed. In strategic mode that's my Aggregated Record; in tactical mode it's my
chance to win. Green and red tell me in under a second whether the moves helped.

**Why this priority**: This is the core question of Impact Analysis ("is this move better?").
Without a visible before/after, the answer depends on the user's memory.

**Independent Test**: In strategic mode, note the Aggregated Record, then make a move that changes
it. Confirm each W/L/T count shows a signed change in the right color. Reset, and confirm every
change marker disappears.

**Acceptance Scenarios**:

1. **Given** no moves, **When** the page shows results, **Then** no change markers appear
   anywhere.
2. **Given** a move that turns the record from 5–11–1 into 7–10–0, **When** results update,
   **Then** W shows `7` with a green `+2`, L shows `10` with a green `−1`, and T shows `0` with a
   gray `−1`.
3. **Given** a move that lowers wins, **When** results update, **Then** the W change is red.
4. **Given** tactical mode where the chance to win goes from 48% to 61%, **When** results update,
   **Then** the headline shows `61%` with a green `+13`.
5. **Given** moves whose combined effect cancels out (a count changes and changes back),
   **When** results update, **Then** that count shows no change marker.

---

### User Story 2 - See which categories and opponents a move changed (Priority: P1)

As a league member evaluating a move, I see which categories got better or worse:
- on the radar, in the ranking or difference tables, and in the category curves;
- against which opponents my results flipped, in the H2H table.

**Why this priority**: The trade-offs of a move (punting one category to gain others) are only
visible per category and per opponent. This is the tool's strategic purpose.

**Independent Test**: Make a move that helps rebounds and hurts assists. Then confirm:
- the radar marks REB green and AST red;
- the ranking table shows a green rank change for REB and a red one for AST;
- the REB curve shows the original distribution grayed out behind the new one.

**Acceptance Scenarios**:

1. **Given** a move, **When** the radar is shown under any scale, **Then** the original shape is
   drawn as a gray outline. Each category whose value moved outward (better) is marked green and
   each that moved inward (worse) red.
2. **Given** a move that lowers your TO average, **When** the ranking table is shown, **Then**
   the Avg change for TO is green (fewer is better) and the Rank change is green if the rank
   number fell.
3. **Given** a move, **When** the Category Breakdown is shown, **Then** every category shows the
   original distribution grayed out behind the current one. Its average label shows the change.
4. **Given** an opponent who was a projected L and is now a projected W, **When** the H2H table
   is shown, **Then** that row's Result is a bold green W.
5. **Given** an opponent who was a projected W and is now a projected L, **When** the H2H table
   is shown, **Then** that row's Result is a bold red L.
6. **Given** tactical mode and a trade with the chosen opponent, **When** the Per Category
   Difference table is shown, **Then** the Opp column shows the opponent's changes too. A drop in
   the opponent's average is green, because it helps you.

---

### User Story 3 - Compare changes after switching scales or settings (Priority: P2)

As a league member, when I switch radar scales or change the window or week, the comparison stays
meaningful: the original is recomputed with the same settings, so only my moves count as change.

**Why this priority**: Without this, changing a setting would show differences caused by the
setting rather than by my moves.

**Independent Test**: Make a move, then change the window from 15 to 10. Confirm the change
markers reflect only the move: the original is also recomputed with a 10-game window.

**Acceptance Scenarios**:

1. **Given** moves and a settings change (window, week, opponent, mode), **When** results
   update, **Then** both the original and the current results use the new settings.
2. **Given** the radar scale is switched, **When** the radar is shown, **Then** the original
   outline and the green/red markers use the same scale as the current shape.
3. **Given** the selected team is switched, **When** results update, **Then** the comparison is
   the new team's original roster against its roster after all moves.

---

### Edge Cases

- **Change smaller than display precision:** if a change rounds to zero at the precision shown
  (e.g. an average shown to 1 decimal), no marker is shown, so tiny changes don't create visual
  noise.
- **Ratio categories:** changes show 3 decimals with no leading zero (`+.012`), as percentages
  are shown today.
- **Missing values:** where the original or the current value is missing (shown as "–", e.g. no
  attempts in a short tactical week), no change is shown for that cell.
- **Teams the user didn't touch:** projections for teams unaffected by any move must not change,
  so they show no markers. A trade changes the other team too, so its effects appear where that
  team is shown (Opp column, H2H row, League and Leader values).
- **Rank ties:** a rank change is the difference in rank numbers under competition ranking (e.g.
  2 → 2 tied shows no change).
- **Reset:** clears all markers immediately.
- **Errors:** if a move is rejected (feature 002 behavior), the markers reflect only the moves
  still applied.
- **Tactical with no opponent:** no comparison is shown (there are no results).

## Requirements *(mandatory)*

### Functional Requirements

**Comparison basis**

- **FR-001**: Every analysis with at least one move MUST also produce the **original** result: the
  loaded rosters with no moves, under the same settings (mode, window, week, opponent, seed,
  iterations).
- **FR-002**: The original and current results MUST be computed so that differences come only
  from the moves. Unaffected teams' projections MUST be identical in both, so they show no change.
- **FR-003**: When there are no moves, no original result is needed, and no change markers MUST
  appear anywhere.

**Change semantics and display**

- **FR-004**: Every change MUST be classified as **better**, **worse**, or **neutral** from the
  selected team's point of view:
  - higher is better for W, win %, chance to win, area scores, and higher-is-better categories;
  - lower is better for L, rank numbers, and lower-is-better categories (TO);
  - ties (T) and league-context values (League average, Leader average) are neutral;
  - in the tactical Opp column, a change that helps the opponent is worse.
- **FR-005**: A change MUST be shown as a small signed value next to the current value, at the
  same precision as the value: `+2`, `−1`, `+18.0`, `+.012`, `+13` (percentage points). Better
  changes are green, worse changes red, and neutral changes muted gray.
- **FR-006**: Changes that round to zero at display precision MUST NOT be shown.

**Places (see the Overview inventory; each MUST be implemented)**

- **FR-007**: **Headline**: strategic W, L, T counts (rules 1 and 4); tactical chance to win
  (rule 2).
- **FR-008**: **Radar**: after moves, the selected team's original shape is drawn as a gray dotted
  outline over the current shapes, in both modes. The opponent's original is not drawn.
  There are no red/green layers or spoke segments; the user tried and removed them. The default
  scale is **Win %**.
- **FR-009**: **Radar scale tabs**: the area score change per tab.
- **FR-010**: **Per Category Ranking** (strategic): changes for Rank, Avg, League, Leader, and
  Win %.
- **FR-011**: **Per Category Difference** (tactical): changes for You, Opp, Diff, and Win %.
- **FR-012**: **Category Breakdown**:
  - the original distribution for the selected team only, grayed out, behind the current one
    (other teams' originals are not drawn);
  - the change shown on each average label.
- **FR-013**: **H2H table**:
  - per opponent: changes for the H2H counts and Win %;
  - the Result styled per the transition table;
  - Total row: changes for both totals.
- **FR-014**: **Roster**: unchanged from 002. Added players keep the yellow "moved" marker.
  Players dropped or traded away are **not** shown in the roster, because that would add rows and
  break FR-019. They appear in the player picker, as a free agent or on their new team.

**Behavior**

- **FR-015**: Changing settings, switching the selected team, or switching the radar scale MUST
  keep the comparison against the original under the new settings (US3).
- **FR-016**: The page MUST still update within the existing 2-second target (002 SC-001) with
  the comparison included.
- **FR-017**: All comparisons and classifications MUST be computed on the server. The page only
  displays them (Constitution stack rule: no statistical or scoring logic in the frontend).
- **FR-018**: The style guide (`docs/style.md`) MUST be amended to define the green and red used
  for better and worse, and the gray used for the original distribution and shape (Constitution
  V: new colors require an amendment).

**Layout stability**

- **FR-019**: Change markers MUST NOT shift the page layout:
  - **Next line:** each change sits on its own line directly below its value, never wrapping the
    value itself.
  - **Reserved line:** that line is always reserved, even with no moves, so column widths, row
    heights and section positions stay the same whether or not markers are shown. Toggling Reset
    doesn't make the page jump.
  - **Record format:** W–L–T records show only the change in **wins** below, e.g. `+2`: green
    when wins go up, red when they go down. Revised at the user's request; this was briefly
    `+W–±L–±T`.
  - **Curve labels:** inside the charts, changes stay inline after the label (`You 412.3 +18.0`),
    because chart label rows are already laid out to avoid collisions.

  This was revised on 2026-10-23 at the user's request; markers were originally inline.

### Key Entities

- **Original result**: the full analysis for the loaded rosters with no moves, under the current
  settings. It is the comparison basis.
- **Change**: for any displayed value, the signed difference (current − original) and its
  classification (better / worse / neutral), rounded to the value's display precision.
- **Result transition**: for each opponent, the original and current projected result (W/L/T)
  and how the change should be styled.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With moves applied, results (including all change markers) still appear in under
  2 seconds for an 18-team league at default settings.
- **SC-002**: With no moves, the page shows zero change markers, in 100% of places in the
  inventory.
- **SC-003**: For a move that affects only the selected team and free agents, every value
  describing an untouched team shows no change, in 100% of cases.
- **SC-004**: Every place in the inventory (9 places) shows changes after a move, as verified
  item by item in acceptance tests.
- **SC-005**: Every change marker's color matches its classification rule (FR-004), including
  the inverted cases (L, rank numbers, TO, Opp column), in 100% of cases.
- **SC-006**: A user can tell whether a move improved their team within 5 seconds of the page
  updating, without remembering any previous number.
- **SC-007**: At the page's maximum width (1,100 px) and at 900 px, showing markers causes no
  line breaks in any inventory place, and no section moves. This is checked by comparing the
  page with and without moves.

## Assumptions

- **Original = no moves:** the comparison basis is the loaded rosters with no moves, not the
  state before the most recent move. That shows the cumulative impact of everything tried. A
  step-by-step comparison (each move against the one before) could be a later option.
- **Colors:** green `#5C8E4E`, taken from the style guide's qualitative palette, marks better.
  Red `#c00`, already the warning color, marks worse. Gray `#ccc`/`#aaa` marks the original
  distribution and outline. The style guide is amended accordingly (FR-018).
- **Delta placement:** deltas appear as small text right after the value; they don't replace it.
  They are deliberately compact (small type, no parentheses in tables, no extra padding) so they
  fit in the existing space (FR-019).
- **Radar markers:** the per-category green/red markers are small enough not to hide the shapes.
  Their exact form (colored segment, dot, or spoke tick) is settled during planning.
- **Picker:** the player picker shows no "what if I added this player" preview. Previewing a move
  before making it is out of scope.
- **Same simulation:** the original and current results come from the same simulation setup, so
  untouched teams are identical (002 research R2). The comparison adds one more analysis per
  request and must stay within the 2-second budget (FR-016).
