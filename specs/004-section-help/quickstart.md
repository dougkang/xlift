# Quickstart & Validation: Section Help

## A. Automated

```bash
cd frontend && npm test && npm run build
```

| Check | Proves |
|---|---|
| Each of the 8 topics: the button exists with an aria-label; a click opens a dialog titled with the section name; Esc and outside clicks close it; focus returns to the button | SC-001, FR-001, FR-004, FR-005 |
| Opening a second help closes the first | FR-005 |
| Content: at most 120 words per topic in both modes; Controls before Reading it; every FR-010 term covered; mode variants differ | SC-002, SC-003, SC-004 |
| Quoted numbers match the result (e.g. the iteration count) | FR-012 |
| Help buttons are inline inside headings and add no blocks | FR-003 |

## B. Browser (manual)

1. At 1,100 px, open each help button in strategic mode, then in tactical mode. Read each popup
   and check it's accurate and short.
2. At 360 px, check every popup fits on screen and scrolls if it's tall.
3. Tab to a help button, press Enter, Tab through the popup, press Esc, and confirm focus is
   back on the button.
4. Confirm no section heading wrapped or moved because of the "?" buttons.
