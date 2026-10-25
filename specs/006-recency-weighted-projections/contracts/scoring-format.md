# Scoring Format Contract Change: `unshrunk_stats`

Base contract: [002 scoring-format.md](../../002-impact-analysis/contracts/scoring-format.md).

## New field

```text
ScoringFormat.unshrunk_stats: tuple[str, ...] = ()
```

These are base stats whose per-game means are **not** shrunk toward the typical player. A
format sets this when a stat's player-to-player differences are mostly skill that a pooled prior
would erase.

- **9cat h2h**: `unshrunk_stats = ("blk",)` (research R4).
- **Default** `()`: every base stat is shrunk.

## Conformance

The shared format conformance suite asserts that every name in `unshrunk_stats` is in
`base_stats`.

## Consumers

Only the core model's prior construction (`build_prior`) reads it. Tools and the API don't.
