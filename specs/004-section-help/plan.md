# Implementation Plan: Section Help

**Branch**: `004-section-help` | **Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-section-help/spec.md`

## Summary

Add a quiet "?" help button inline with each of the 8 section headings. Each one opens an
accessible, viewport-clamped popover with concise copy, ordered Controls → Reading it → Terms.

- **Content:** comes from a single module, uses live values (iterations, window, capacity,
  opponent), and switches between strategic and tactical variants.
- **Popover:** a small custom component behind a one-at-a-time provider, with no new
  dependencies.
- **Backend:** no changes.

## Technical Context

**Language/Version**: TypeScript 5.9, React 19 (frontend only)

**Primary Dependencies**: none new

**Storage**: N/A

**Testing**: Vitest + React Testing Library: behavior per topic, a content word-count and
coverage test, and a layout test

**Target Platform**: Browser, 360–1,100 px+

**Project Type**: Web app (existing `frontend/`)

**Performance Goals**: The popover opens instantly; the content is static apart from a few
interpolated numbers

**Constraints**:
- at most 120 words per popup;
- Controls listed first;
- no layout shift;
- focus management;
- style guide compliance (no new colors)

**Scale/Scope**: 8 topics × 2 modes; 3 new components (`HelpProvider`, `HelpButton`,
`HelpPopover`) plus the content module

## Constitution Check

*GATE: checked before Phase 0 research and again after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| I–IV (modeling) | ✅ N/A | No change to statistics. The copy describes the existing definitions (ratio of means, TO direction, win-rate ties counted half) and doesn't redefine them. |
| V. Visualization | ✅ | Quiet controls and a bordered popover with no radius or shadow; no new colors. The no-layout-shift rule follows the 003 precedent. |
| VI. Data source orthogonality | ✅ N/A | — |
| VII. Modular core | ✅ | The frontend only. The copy is presentation, not domain logic, and quoted numbers come from the API. |
| Tech stack | ✅ | React + TS; no new libraries. |
| Quality gates | ✅ | Tests enforce conciseness, ordering, term coverage and mode variants. |

**Post-design re-check**: still passing.

## Project Structure

```text
specs/004-section-help/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/ui.md
└── tasks.md            # /speckit-tasks

frontend/src/
├── help/
│   ├── content.ts      # HELP topics (single source, from the spec appendix)
│   ├── HelpProvider.tsx  # openId context
│   ├── HelpButton.tsx
│   └── HelpPopover.tsx   # portal, positioning, focus, close
├── components/{Controls,RecordHeadline,CategoryTable,Roster,RecordTable,CategoryCurves}.tsx  # + <HelpButton>
├── App.tsx             # HelpProvider + HelpContext; Radar/Players buttons
└── styles/base.css     # .help-button, .help-popover
frontend/tests/
├── help.test.tsx           # open/close/focus/one-at-a-time for all 8
└── help-content.test.ts    # ≤120 words, ordering, FR-010 coverage, mode variants
```

**Structure Decision**: a self-contained `help/` folder. Existing components gain only an inline
`<HelpButton>` next to each heading.

## Complexity Tracking

No violations.
