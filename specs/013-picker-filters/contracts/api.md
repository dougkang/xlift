# API contract: `POST /api/impact/players`

```text
PlayersRequest (adds)
  positions: ["G" | "F" | "C"] = []
  owners: ["fa" | int] = []
  sort_categories: [str] = []          # category keys, e.g. ["reb", "blk"]

PlayerRow (adds)
  sort_xlift: float | null
```

- Filters combine with `query` and each other (AND); within a list, any match (OR).
- With `sort_categories`, rows are ordered by `sort_xlift` (free agents first, then name);
  otherwise unchanged.
- Unknown category key → 422.
