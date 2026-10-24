# Contract: Help Buttons and Popups

## `<HelpButton topic={TopicId} />`

- **Element:** `<button class="help-button" aria-label="Help: <title>" aria-haspopup="dialog"
  aria-expanded={open}>?</button>`. It sits inline after the section heading text (research R1).
- **Opening and closing:** a click toggles the popup. Opening one topic closes any other.

## `<HelpPopover>` (portal)

```text
┌───────────────────────────────┐
│ Radar                         │   ← title (bold, focus target); no close button
│ CONTROLS                      │
│ Rank / Average / Win % — …    │   ← bold name — effect
│ Score — …                     │
│ READING IT                    │
│ • Your team is navy; …        │
│ TERMS                         │   ← optional
│ Area score — …                │
└───────────────────────────────┘
```

- **Accessibility:** `role="dialog"` with `aria-labelledby` pointing at the title.
- **Size and position:** the width is `min(22rem, 100vw − 32px)`, and it is placed below the
  button, or above it when there's no room. It is clamped 16px inside the viewport and scrolls
  internally when taller than the viewport.
- **Closing:** Esc or a mouse-down outside closes it, and focus returns to the button.
- **Style:** a 1px `#111` border, `#fff` background, and no radius or shadow. Labels use
  column-header style.

## Topics (all 8)

The content is defined in `frontend/src/help/content.ts`, seeded from the spec appendix.

| TopicId | Anchor | Mode variants |
|---|---|---|
| `settings` | End of the first controls row | Tactical adds vs and Week |
| `headline` | After "Aggregated Record" / "Chance to Win" | Yes |
| `radar` | Radar divider | — |
| `categoryTable` | Per Category Ranking / Difference divider | Yes |
| `roster` | Roster divider | Tactical adds G |
| `h2h` | H2H divider | — |
| `breakdown` | Category Breakdown divider | Yes |
| `players` | Players divider | Tactical adds G |

**Update (005):** the settings topic no longer lists vs or Week, and a tenth topic,
`opponentRoster`, explains the opponent's read-only roster, which replaces H2H in tactical mode.
