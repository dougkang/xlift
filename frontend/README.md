# ffmodel frontend

The Impact Analysis page: React + TypeScript + Vite, a D3 radar, and Observable Plot curves. It
only renders what the API returns. All statistics and roster rules live in the backend
(see the [constitution](../.specify/memory/constitution.md), Technology Stack).

## Prerequisites

- Node 22 LTS (`brew install node@22`)
- The backend running: `cd ../backend && uv run ffm serve`

## Scripts

```bash
npm install
npm run dev        # http://localhost:5173, proxies /api to http://localhost:8000
npm test           # Vitest + Testing Library, with a mocked API
npm run build      # type-check + production bundle in dist/ (served by `ffm serve`)
npm run gen:api    # regenerate src/api/schema.d.ts from the running backend's OpenAPI schema
```

Regenerate the types whenever the backend's API models change. The test fixtures in
`tests/fixtures/` are real API responses from the backend's fixture league; refresh them with
`cd ../backend && uv run python -m tests.fixtures.export_frontend_fixtures`.

## Layout

```text
src/api/         generated schema types + typed client
src/state/       settings + moves (sessionStorage)
src/components/  Controls, RecordHeadline, Radar, CategoryTable, CategoryCurves, Roster,
                 RecordTable (H2H), PlayerPicker, SwapDialog
src/styles/      tokens + base styles from docs/style.md
```
