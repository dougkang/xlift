# Feature Specification: Section Help

**Feature Branch**: `004-section-help`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "implement help buttons next to each section that open a popup explaining how to use and interpret each section. the help should be concise, succinct. it should start by explaining any UI elements and what they control. some of the less obvious stats should also be explained."

## Overview

Impact Analysis packs a lot into one page: modes, scales, simulated records, win rates, area
scores, and before/after markers. This feature adds a small **help button** next to each section
heading. It opens a short popup that:
1. starts with the section's **controls**, and what each one changes;
2. then says **how to read** the section;
3. explains the **less obvious statistics** in plain words.

The help is reference material. It is short enough to read in seconds and never covers the
data longer than the user wants.

### Sections that get help (inventory)

| # | Section | Mode-specific content |
|---|---|---|
| 1 | Analysis settings (Last X games, League, Team, vs, Week, Reset, Strategic/Tactical) | Tactical adds vs and Week |
| 2 | Team headline (Aggregated Record / Chance to Win) | Yes |
| 3 | Radar (Rank / Average / Win % tabs, area scores) | — |
| 4 | Per Category Ranking (strategic) / Per Category Difference (tactical) | Yes |
| 5 | Roster | Tactical adds the G column |
| 6 | H2H | — |
| 7 | Category Breakdown | Yes (different overlays) |
| 8 | Players (picker, swap) | Tactical adds the G column |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand a section without leaving the page (Priority: P1)

As a league member looking at an unfamiliar section, I press its help button, read a short
explanation of its controls and how to read it, and close it to get back to the data.

**Why this priority**: Most of the tool's value depends on reading the projections correctly.
Several measures (win rate, area score, aggregated record) aren't standard fantasy terms.

**Independent Test**: For every section in the inventory:
1. press its help button;
2. confirm a popup opens with the section's title, a controls part first (where the section has
   controls), then how to read it;
3. close it with Esc or by clicking outside;
4. confirm focus returns to the help button.

**Acceptance Scenarios**:

1. **Given** any section in the inventory, **When** I look at its heading, **Then** a small help
   button sits right next to it, labeled for screen readers as "Help: <section name>".
2. **Given** I press a help button, **When** the popup opens, **Then** it shows:
   - the section name as its title;
   - a **Controls** part listing each control in the section and what it changes, if the
     section has controls;
   - a **Reading it** part;
   - optionally a **Terms** part with short definitions.
3. **Given** an open popup, **When** I press Esc or click anywhere
   outside it, **Then** it closes and keyboard focus returns to the help button that opened it.
4. **Given** an open popup, **When** I open another section's help, **Then** the first closes;
   only one popup is open at a time.
5. **Given** the page shows changes after moves, **When** I open help for a section with change
   markers, **Then** the help briefly explains them (green/red, the line below the value, the
   dotted "before" shapes).

---

### User Story 2 - Help that matches what I'm looking at (Priority: P2)

As a league member switching between strategic and tactical mode, the help describes the version
of the section I'm actually seeing.

**Why this priority**: several sections change meaning between modes (record vs. chance to win,
ranking vs. difference table, overlays). Help for the other mode would mislead.

**Independent Test**: Open the headline's help in strategic mode; it explains the Aggregated
Record. Switch to tactical and open it again; it explains Chance to Win.

**Acceptance Scenarios**:

1. **Given** strategic mode, **When** I open help for the headline, the category table, and the
   breakdown, **Then** they describe: the Aggregated Record; Per Category Ranking (Rank, Avg,
   League, Leader, Win %); and the leader and league overlays.
2. **Given** tactical mode, **When** I open the same helps, **Then** they describe: Chance to
   Win and the opponent line; Per Category Difference (You, Opp, Diff, Win %); and the opponent
   overlay.
3. **Given** a number the help quotes (e.g. the simulation count or the default window),
   **When** it's shown, **Then** it matches the value the page is actually using.

---

### Edge Cases

- **Small screens:** at narrow widths the popup stays fully on screen. It never extends past the
  viewport, and it scrolls internally if needed.
- **No data yet:** sections that aren't shown (e.g. tactical results before an opponent is
  chosen) don't show a help button. The settings help is always available.
- **Warnings:** the headline help mentions the "Choose an opponent" and "no games remaining"
  messages so they're not confusing.
- **Layout:** help buttons don't change the layout. They sit inline with headings and take no
  extra rows.
- **Print and copy:** the help text is plain text and selectable.

## Requirements *(mandatory)*

### Functional Requirements

**Help buttons**

- **FR-001**: Every section in the inventory MUST have a help button placed immediately after its
  heading, on the same line.
- **FR-002**: The button MUST follow the style guide's quiet-control rules: no box, muted until
  hovered, and a visible keyboard focus. It MUST have an accessible name "Help: <section name>".
- **FR-003**: Help buttons MUST NOT change the page layout. Adding them causes no new lines and
  no shifted sections.

**Popup**

- **FR-004**: Pressing a help button MUST open a popup anchored near the button. It MUST have a
  title (the section name). It has no close button; Esc or a click outside closes it.
- **FR-005**: The popup MUST close on Esc and on a click outside it. Focus
  MUST then return to the help button. Only one popup MUST be open at a time.
- **FR-006**: The popup MUST stay within the viewport at every width down to 360 px, scrolling
  internally if needed.
- **FR-007**: While open, the popup MUST move keyboard focus into itself and be announced to
  screen readers as a dialog with its title.

**Content**

- **FR-008**: Each popup MUST be ordered: **Controls** first (when the section has controls),
  each control named exactly as it appears on screen with what it changes; then **Reading it**;
  then optional **Terms**.
- **FR-009**: Content MUST be concise. Each popup is **at most 120 words**, uses short bullets,
  and contains no paragraphs longer than two sentences.
- **FR-010**: The less obvious statistics MUST be explained wherever they appear:
  - **Aggregated Record:** the simulated matchup record against every other team.
  - **Chance to Win:** the share of simulations in which you win the matchup.
  - **H2H:** projected categories won, lost and tied against one opponent.
  - **Win %:** in the ranking table, the chance of beating a random league opponent in that
    category, with ties counting half; in the difference table and H2H, the chance against that
    opponent.
  - **Area score:** your radar's area relative to the league's largest, where the top team is
    100.
  - **Average scale:** each category min-max scaled across the league.
  - **Rank:** 1 is best; TO ranks lower-is-better.
  - **League** and **Leader:** the league average and the leader's average.
  - **Asterisk:** fewer games in the window than requested.
  - **G:** games left in the week.
  - **Reserve slots** (IL/NA).
  - **FG% / FT%:** computed from total makes ÷ attempts.
  - **Change markers:** green is better and red is worse; the change sits on the line below;
    the dotted outline or "(before)" is the original roster.
- **FR-011**: Mode-specific sections MUST show the content for the current mode (US2).
- **FR-012**: Numbers quoted in help (simulation count, default window, roster capacity) MUST come
  from the values the page is using, not be hard-coded.
- **FR-013**: The help content MUST be maintained in one place, so a change to a section's
  behavior has a single text to update. The draft content in the appendix is the starting point.

### Key Entities

- **Help topic**: a section's help: its title, Controls items (name → effect), Reading-it
  bullets, and Terms (term → definition), with optional strategic/tactical variants.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the 8 inventory sections have a help button with working open and close
  (button, Esc, click outside), as verified section by section.
- **SC-002**: Every popup is 120 words or fewer, and every one with controls lists them first.
- **SC-003**: Every term in FR-010 is defined in at least one popup, as checked against the list.
- **SC-004**: Mode-specific popups show the correct variant in both modes, in 100% of the
  4 mode-specific sections.
- **SC-005**: At 1,100 px and 360 px wide, showing help buttons causes no layout shift, and every
  popup is fully visible.
- **SC-006**: A first-time user can explain what "Win %" and the area score mean after reading
  the relevant popup once, in under 30 seconds.

## Assumptions

- **Help text lives in the page:** help is static explanatory copy, not domain logic, so it
  belongs in the page (the constitution's no-statistics-in-frontend rule doesn't apply).
  Quoted numbers come from the API response (FR-012).
- **Popup styling:** the popup follows the style guide (no rounded corners or shadows; a 1px
  black border, white background, small text). It's a lightweight anchored panel, not a
  full-screen modal.
- **Button glyph:** "?" in small muted text, consistent with the subtle-controls rule.
- **No onboarding:** no tutorial or first-visit tour. Help is on demand only.
- **English only.**

## Appendix: Draft help content

Each popup has a "Controls" part (where the section has controls), then "Reading it", then
"Terms". The final copy is refined during implementation within the 120-word limit.

**1. Analysis settings**
- *Controls:*
  - **Strategic / Tactical**: long-run view against the whole league, or this week against one
    opponent.
  - **Last X games**: how many recent games each player's projection uses.
  - **League** and **Team**: whose team you're analyzing.
  - **vs** (tactical): this week's opponent.
  - **Week** (tactical): the matchup dates; only games left in it count.
  - **Reset**: undo every roster move.
- *Reading it:* every number on the page comes from simulating `N` matchup weeks. Moves are
  hypothetical and never change your real league.

**2. Team headline**
- *Strategic:* **Aggregated Record** is your projected W–L–T if you played every other team once;
  a matchup counts as a W if you win it in more than half the simulations. The number below is
  the change in wins from your moves.
- *Tactical:* **Chance to Win** is how often you beat this opponent across the simulations,
  counting only games left this week.

**3. Radar**
- *Controls:*
  - **Rank / Average / Win %**: how far out each spoke goes. Rank 1, the league's best average,
    or a 100% win rate is at the edge.
  - **Score** next to each tab: your shape's area relative to the league's biggest; the top
    team is 100.
- *Reading it:* your team is navy; other teams are outlines. Where another outline pokes past
  yours, that team beats you in the category. A dotted outline is your shape before moves.

**4a. Per Category Ranking** (strategic)
- *Reading it:*
  - **Rank:** 1 is best.
  - **Avg:** your projected weekly total.
  - **League:** the league average.
  - **Leader:** the best team's average; hover it to see the team.
  - **Win %:** your chance of beating a random league team in this category.

**4b. Per Category Difference** (tactical)
- *Reading it:*
  - **You / Opp:** projected totals for the rest of the week.
  - **Diff:** green favors you, red favors them.
  - **Win %:** your chance of winning this category against this opponent.

**5. Roster**
- *Controls:* **−** drops a player to free agency (hypothetical).
- *Reading it:*
  - Muted rows are IL/NA reserve slots; they don't play in the simulation.
  - Red text is the player's status.
  - **\*** means fewer games in the window than requested.
  - **G** (tactical) is games left this week.
  - Yellow rows were changed by your moves.

**6. H2H**
- *Reading it:*
  - One row per opponent.
  - **H2H:** projected categories won–lost–tied against them in the simulations.
  - **Win:** your chance to win the matchup.
  - **Result:** W if you win in more than half the simulations. A bold green W means your moves
    turned a loss into a win; bold red means the reverse.
  - **Total:** sums every row.

**7. Category Breakdown**
- *Reading it:*
  - Each chart shows the spread of your simulated weekly totals.
  - Lines mark averages. In strategic mode the League Leader and League Average are overlaid;
    in tactical mode, your opponent.
  - A dotted "(before)" shape is your distribution before moves.
  - FG% and FT% come from total makes ÷ attempts.

**8. Players**
- *Controls:*
  - **Search:** filter by name; accents are ignored.
  - **+** adds a free agent to an open slot.
  - On another team's player, **+** opens a swap: give them a roster player (a trade) or a free
    agent.
- *Reading it:*
  - Free agents are listed first.
  - Red text is status.
  - **\*** means a short history.
  - **G** (tactical) is games left this week.
