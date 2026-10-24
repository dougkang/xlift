---
description: "Task list for 004 Section Help"
---

# Tasks: Section Help

**Input**: Design documents from `specs/004-section-help/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui.md, quickstart.md

**Tests**: Included. The spec's success criteria (SC-001–SC-004) are checked by automated tests
(quickstart §A).

All paths are relative to the repo root. The work is frontend only: no backend, API or type
regeneration.

## Phase 1: Setup

- [X] T001 Create the `frontend/src/help/` folder and confirm the baseline is green: `cd frontend && npm test && npm run build`

## Phase 2: Foundational (blocks both stories)

- [X] T002 Define the types in `frontend/src/help/content.ts`:
  - `TopicId` = `"settings" | "headline" | "radar" | "categoryTable" | "roster" | "h2h" | "breakdown" | "players"`;
  - `HelpContext` = `{ mode: "strategic" | "tactical"; iterations: number; window: number; capacity: number | null; opponentName: string | null }`;
  - `HelpTopic` = `{ title: string; controls?: [string, string][]; reading: string[]; terms?: [string, string][] }`;
  - an exported `HELP: Record<TopicId, (ctx: HelpContext) => HelpTopic>`, initially with placeholder topics.

  Also add `helpText(topic)` (plain text for word counting) and `wordCount(text)` helpers.
- [X] T003 Create `frontend/src/help/HelpProvider.tsx`:
  - a React context holding `openId: TopicId | null`, `open(id)`, `close()`, and the `HelpContext` value;
  - "At most one popup open (FR-005)": opening an id replaces the current one;
  - export the `useHelp()` hook.

## Phase 3: User Story 1 — Understand a section without leaving the page (P1) 🎯 MVP

**Goal**: Every one of the 8 sections has a quiet "?" button. It opens an anchored, accessible
popup ordered Controls → Reading it → Terms, which closes on Esc, ×, or a click outside, and
returns focus to the button.

**Independent test**: For each section, press "?" and check that the dialog title is the section
name and Controls comes first. Close it each of the three ways and check that focus returns to
the button (spec US1).

### Tests for User Story 1

- [X] T004 [P] [US1] Write `frontend/tests/help.test.tsx`, which renders `App` with the strategic fixture, plus the tactical fixture for tactical-only sections. For each of the 8 topics it checks:
  - a button named "Help: <title>" exists;
  - a click opens `role="dialog"` labelled by the title;
  - Esc, the × button and a `mousedown` on `document.body` each close it;
  - focus returns to the button after each close;
  - opening a second help closes the first.

  This covers FR-001, FR-004, FR-005, FR-007 and SC-001.
- [X] T005 [P] [US1] Write `frontend/tests/help-content.test.ts`. For every topic, in both modes, with a representative `HelpContext`, it checks:
  - "at most 120 words" via `wordCount(helpText(topic))` (FR-009);
  - `controls`, when present, render before Reading it (FR-008);
  - every FR-010 term appears in at least one topic in at least one mode. The term list is Aggregated Record, Chance to Win, H2H, Win %, Area score, Average, Rank, League, Leader, asterisk/fewer games, G, IL/NA reserve, FG%/FT% makes ÷ attempts, and green/red/dotted/(before) change markers (SC-003).

### Implementation for User Story 1

- [X] T006 [P] [US1] Create `frontend/src/help/HelpButton.tsx`:
  - `<button type="button" className="help-button" aria-label={"Help: " + title} aria-haspopup="dialog" aria-expanded={open}>?</button>`;
  - it toggles its topic through `useHelp()`;
  - it keeps a ref to the button and renders `<HelpPopover>` when open.
- [X] T007 [P] [US1] Create `frontend/src/help/HelpPopover.tsx`:
  - **Rendering:** a portal to `document.body`; `role="dialog"`, `aria-modal="false"`, and `aria-labelledby` set to the title id; the title has `tabIndex=-1` and receives focus on mount.
  - **Content:** a × close button labelled "Close help", then sections in the fixed order CONTROLS (bold name — effect), READING IT (bullets), TERMS (bold term — definition), omitting empty ones.
  - **Position:** from the anchor's `getBoundingClientRect()`, recomputed on resize and scroll:
    - width `min(22rem, 100vw − 32px)`;
    - left clamped to [16, innerWidth − width − 16];
    - below the anchor, flipped above when there is no room;
    - `max-height: calc(100vh − 32px)` with `overflow:auto` (FR-006).
  - **Closing:** on Esc (keydown on document), the × button, or `mousedown` outside both the popover and the anchor. Each calls `close()` and returns focus to the anchor.
- [X] T008 [P] [US1] Add `.help-button` and `.help-popover` styles to `frontend/src/styles/base.css`, per research R1/R5, using no new colors.
  - `.help-button`:
    - inline, no border or background, color `var(--muted)`, font-size 0.65rem, line-height 1;
    - a small left margin and vertical-align so it doesn't change the heading height;
    - yellow fill on hover and black outline on `:focus-visible`;
    - `text-transform:none` and `letter-spacing:normal` inside the uppercase dividers.
  - `.help-popover`:
    - fixed position, 1px `#111` border, `#fff` background, no radius or shadow, text at `--data-size`, padding 0.6rem 0.75rem, and a z-index above the charts;
    - section labels in column-header style;
    - normal text-align, case and weight (it sits outside the dividers, but reset them anyway).
- [X] T009 [US1] Write the final copy for all 8 topics in `frontend/src/help/content.ts`, from the spec appendix:
  - include the user's edits ("TO is better when lower" removed from Rank in the category table; "in the simulations" added to H2H);
  - use exact on-screen control names;
  - interpolate `ctx.iterations` (formatted with thousands separators), `ctx.window` and `ctx.capacity` instead of literals (FR-012);
  - include the change-marker explanation where markers appear (US1 scenario 5).

  Tactical variants for headline, categoryTable and breakdown are completed in US2; give them the strategic copy for now.
- [X] T010 [US1] Wrap the app in `<HelpProvider>` in `frontend/src/App.tsx`:
  - build the `HelpContext` from the current mode, `result.settings.iterations`, the window setting, the selected league's roster capacity, and the opponent's name, using fallbacks when no result is loaded yet;
  - add `<HelpButton topic="radar" />` inside the Radar `section-divider` h3 and `<HelpButton topic="players" />` inside the Players divider.
- [X] T011 [P] [US1] Add `<HelpButton topic="settings" />` at the end of the first controls row in `frontend/src/components/Controls.tsx`. The settings help is always shown (edge case "No data yet").
- [X] T012 [P] [US1] Add `<HelpButton topic="headline" />` after the "Aggregated Record" / "Chance to Win" label in `frontend/src/components/RecordHeadline.tsx`.
- [X] T013 [P] [US1] Add `<HelpButton topic="categoryTable" />` inside both divider headings ("Per Category Ranking" and "Per Category Difference") in `frontend/src/components/CategoryTable.tsx`.
- [X] T014 [P] [US1] Add `<HelpButton topic="roster" />` inside the "Roster" divider in `frontend/src/components/Roster.tsx`.
- [X] T015 [P] [US1] Add `<HelpButton topic="h2h" />` inside the "H2H" divider in `frontend/src/components/RecordTable.tsx`.
- [X] T016 [P] [US1] Add `<HelpButton topic="breakdown" />` inside the "Category Breakdown" divider in `frontend/src/components/CategoryCurves.tsx`.
- [X] T017 [US1] Run `cd frontend && npm test`, then fix any existing tests broken by the added button text. Headings now contain "?", so use `getByRole('heading', {name: /Radar/})` or scoped queries. T004 and T005 must pass.

**Checkpoint**: US1 is complete. All 8 helps work with strategic copy.

## Phase 4: User Story 2 — Help that matches what I'm looking at (P2)

**Goal**: Mode-specific sections describe the version on screen, and quoted numbers match the
live settings.

**Independent test**: Open the headline help in strategic mode and check it explains Aggregated
Record. Switch to tactical and check it explains Chance to Win (spec US2).

### Tests for User Story 2

- [X] T018 [P] [US2] Extend `frontend/tests/help-content.test.ts`:
  - for each of `headline`, `categoryTable` and `breakdown`, the strategic and tactical texts differ;
  - strategic headline mentions "Aggregated Record", tactical mentions "Chance to Win";
  - strategic categoryTable mentions Rank, Avg, League, Leader and Win %; tactical mentions You, Opp, Diff and Win %;
  - strategic breakdown mentions the leader and league overlays; tactical mentions the opponent overlay;
  - settings, roster and players mention vs/Week/G only in tactical;
  - a context with `iterations: 12345` renders "12,345", and changing `window` or `capacity` changes the text (FR-012, SC-004).
- [X] T019 [P] [US2] Extend `frontend/tests/help.test.tsx`: with the tactical fixture, open headline help and assert the dialog contains "Chance to Win". With the strategic fixture, assert it contains "Aggregated Record" and the fixture's iteration count.

### Implementation for User Story 2

- [X] T020 [US2] Write the tactical variants in `frontend/src/help/content.ts`, branching on `ctx.mode`:
  - **headline:** Chance to Win, the opponent line, and the "Choose an opponent" / "no games remaining" warnings;
  - **categoryTable:** Per Category Difference, with columns You / Opp / Diff / Win % vs this opponent;
  - **breakdown:** the opponent overlay and the "(before)" line;
  - **settings:** adds the vs and Week controls;
  - **roster and players:** add G = games left in the week.

  Keep every variant at 120 words or fewer.
- [X] T021 [US2] Run `cd frontend && npm test` and confirm T018 and T019 pass.

**Checkpoint**: US1 and US2 are both complete.

## Phase 5: Polish & Cross-Cutting

- [X] T022 [P] Add a layout test to `frontend/tests/help.test.tsx` (FR-003, SC-005):
  - every `.help-button` sits inside its heading element (or the controls row) rather than adding a sibling block;
  - no help button renders for sections that aren't shown (e.g. tactical with no opponent: no H2H help).
- [X] T023 [P] Document the help button and popover (glyph, placement, colors, border, and no layout shift) in a "Help" subsection of `docs/style.md`.
- [X] T024 Run `cd frontend && npm run build`, then restart `ffm serve` (`pkill -f "ffm serve"`, then start it in the background on :8000).
- [ ] T025 Run the manual checks in quickstart §B at 1,100 px and 360 px in both modes, and trim any copy that reads long.

## Dependencies & Execution Order

- **Setup (T001)** → **Foundational (T002–T003)** → **US1 (T004–T017)** → **US2 (T018–T021)** → **Polish (T022–T025)**.
- **Within US1:**
  - T004 and T005 can be written first (TDD).
  - T006, T007 and T008 run in parallel; T009 is content only.
  - T010 depends on T003 and T006.
  - T011–T016 are parallel (different files) after T006.
  - T017 runs last.
- **US2 dependencies:** US2 depends on US1's content module and buttons. It changes only `content.ts` and the tests.

## Parallel Example: User Story 1

```text
T006 HelpButton.tsx   |  T007 HelpPopover.tsx  |  T008 base.css
then: T011 Controls | T012 RecordHeadline | T013 CategoryTable | T014 Roster | T015 RecordTable | T016 CategoryCurves
```

## Implementation Strategy

- **MVP:** Phases 1–3 (US1). All 8 sections get working, accessible help with strategic copy.
- **Increment:** Phase 4 (US2) adds the mode-specific copy and live numbers.
- **Finish:** Phase 5 adds the layout test, style docs and a manual check.
