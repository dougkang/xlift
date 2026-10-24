# Data Model: Section Help

There are no backend or schema changes. These types live only in the frontend
(`frontend/src/help/`).

| Type | Fields | Rules |
|---|---|---|
| `TopicId` | `"settings"`, `"headline"`, `"radar"`, `"categoryTable"`, `"roster"`, `"h2h"`, `"breakdown"`, `"players"` | The 8 sections in the spec's inventory |
| `HelpContext` | `mode: "strategic" \| "tactical"`, `iterations: number \| null` (null before the first result), `window: number`, `capacity: number \| null`, `opponentName: string \| null` | Built from the current `AnalysisResult.settings`, the league detail, and the matchups (FR-012) |
| `HelpTopic` | `title: string`, `controls?: [name, effect][]`, `reading: string[]`, `terms?: [term, definition][]` | Rendered in the order Controls → Reading it → Terms (FR-008). At most 120 words in total (FR-009) |
| `HELP` | `Record<TopicId, (ctx) => HelpTopic>` | The single source of help copy (FR-013). Mode-specific topics branch on `ctx.mode` |
| Help state | `openId: TopicId \| null` in `HelpProvider` | At most one popup open (FR-005) |
