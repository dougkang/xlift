# Phase 0 Research: Section Help

This feature is frontend only. The backend doesn't change: help is explanatory copy, and the
numbers it quotes already come from the API response.

## R1. Where each help button goes

| # | Section | Anchor |
|---|---|---|
| 1 | Settings | End of the first controls row ("Last X games"); the settings have no heading |
| 2 | Team headline | After the right-hand label ("Aggregated Record" / "Chance to Win") |
| 3 | Radar | Inside the "Radar" section divider, after the text |
| 4 | Per Category Ranking / Difference | Inside the section divider |
| 5 | Roster | Inside the section divider |
| 6 | H2H | Inside the section divider |
| 7 | Category Breakdown | Inside the section divider |
| 8 | Players | Inside the section divider |

**The button:**
- a `<button class="help-button">` showing "?";
- muted (`--muted`) at 0.65rem, borderless, with the yellow fill on hover and the black outline
  on keyboard focus (style guide quiet controls);
- `aria-label="Help: <title>"`, `aria-haspopup="dialog"`, and `aria-expanded`;
- inline, so dividers keep their single line (FR-003).

## R2. Popup mechanics (no new dependency)

**Decision**: a small custom `HelpPopover` component.

- **Rendering:** through a portal on `document.body` with `role="dialog"`, `aria-modal="false"`,
  and `aria-labelledby` pointing at its title.
- **Position:** placed under its button, using `getBoundingClientRect()` on open and on window
  resize or scroll.
  - Its width is `min(22rem, 100vw − 32px)`.
  - Its left edge is clamped to [16, viewport − width − 16].
  - It flips above the button when there's no room below.
  - It sets `max-height: calc(100vh − 32px)` with internal scrolling (FR-006).
- **Closing:** on Esc, on the × button, and on `mousedown` outside both the popover and its
  button. Focus then returns to the button.
- **Focus on open:** moves to the popover's title, which has `tabIndex=-1` (FR-005, FR-007).
- **One at a time:** a `HelpProvider` context holds `openId`, and opening one closes any other
  (FR-005).

**Alternatives considered:**
- **The native `<dialog>` and Popover API:** good, but jsdom support is partial, which makes the
  tests brittle, and anchored positioning is still uneven across browsers.
- **A UI library:** an extra dependency for a small component.

## R3. Content: one module, data not markup (FR-008, FR-012, FR-013)

**Decision**: `frontend/src/help/content.ts` exports
`HELP: Record<TopicId, (ctx: HelpContext) => HelpTopic>`.

- **`HelpContext`:** `mode`, `iterations`, `window`, `capacity` and `opponentName`, all taken
  from the current `AnalysisResult` and settings, so quoted numbers are live (FR-012).
- **`HelpTopic`:** `{ title, controls?: [name, effect][], reading: string[], terms?: [term,
  definition][] }`.
- **One renderer:** `HelpPopover` renders every topic in the fixed order Controls → Reading it →
  Terms (FR-008).
- **Starting copy:** the spec's appendix, as edited by the user.

## R4. Enforcing "concise" (FR-009, SC-002, SC-003)

**Decision**: a unit test renders every topic in both modes with a representative context and
checks four things:
1. **Word count:** at most 120 words. Words are counted on the plain text of the title, controls,
   reading bullets and terms.
2. **Controls first:** wherever the section has controls, they come before Reading it.
3. **Required terms:** every FR-010 term appears in at least one topic, checked against a fixed
   list.
4. **Mode variants:** topics 2, 4 and 7 differ between strategic and tactical.

## R5. Style

The popover follows `docs/style.md`:
- a 1px `#111` border, white background, and no radius or shadow;
- the title in bold;
- section labels in column-header style (`CONTROLS`, `READING IT`, `TERMS`);
- body text at `--data-size`;
- control and term names bold.

It adds no new colors.
