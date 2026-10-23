# Contract: Scoring Format Interface (`ffmodel.core.scoring`)

This is Constitution II made concrete. The simulation engine, the tool and the API depend only on
this interface. Adding a format, for example 8cat or points, means writing one module, registering
it, and passing the conformance suite. Nothing else changes.

```python
@dataclass(frozen=True)
class Category:
    key: str                       # "fg_pct"
    label: str                     # "FG%"
    kind: Literal["additive", "ratio"]
    stat: str | None = None        # additive: raw stat key, e.g. "tov"
    numerator: str | None = None   # ratio: "fgm"
    denominator: str | None = None # ratio: "fga"
    higher_is_better: bool = True  # TO: False
    decimals: int = 0              # FG%: 3, shown as .473

class ScoringFormat(Protocol):
    id: str
    name: str
    categories: tuple[Category, ...]
    base_stats: tuple[str, ...]                    # drawn by the simulation
    derived_stats: Mapping[str, Callable[[Mapping[str, ndarray]], ndarray]]  # e.g. pts

    def category_values(self, totals: Mapping[str, ndarray]) -> ndarray: ...
        # totals[stat]: shape (iterations,) team totals → (iterations, n_categories)
        # ratio categories: numerator.sum / denominator.sum per iteration; NaN when denominator == 0

    def compare(self, a: ndarray, b: ndarray) -> ndarray: ...
        # (iterations, n_categories) x2 → int8 in {+1, 0, -1}, from a's point of view
        # direction-aware; NaN on either side → 0 (tie)

    def matchup(self, outcomes: ndarray) -> ndarray: ...
        # (iterations, n_categories) → (iterations,) in {+1, 0, -1}
        # 9cat h2h: sign(#wins - #losses)

    def projected_average(self, totals: Mapping[str, ndarray]) -> ndarray: ...
        # (n_categories,) used for ranks and tactical differences.
        # additive: mean; ratio: mean(numerator) / mean(denominator)  — ratio of means

def get_format(format_id: str) -> ScoringFormat   # raises UnsupportedFormat
def available_formats() -> tuple[str, ...]
```

## `9cat_h2h` (the first implementation)

| Key | Label | Kind | Source | Higher is better | Decimals |
|---|---|---|---|---|---|
| `pts` | PTS | additive | `pts` (derived = 2·fgm + fg3m + ftm) | ✓ | 0 |
| `reb` | REB | additive | `reb` | ✓ | 0 |
| `ast` | AST | additive | `ast` | ✓ | 0 |
| `stl` | STL | additive | `stl` | ✓ | 0 |
| `blk` | BLK | additive | `blk` | ✓ | 0 |
| `fg3m` | 3PM | additive | `fg3m` | ✓ | 0 |
| `fg_pct` | FG% | ratio | `fgm` / `fga` | ✓ | 3 |
| `ft_pct` | FT% | ratio | `ftm` / `fta` | ✓ | 3 |
| `tov` | TO | additive | `tov` | ✗ | 0 |

`base_stats` = (`fgm`, `fga`, `fg3m`, `ftm`, `fta`, `reb`, `ast`, `stl`, `blk`, `tov`).

## Conformance suite (`tests/scoring/test_conformance.py`)

The suite is parametrized over `available_formats()`. Every format must pass all eight checks:

1. **Base stats exist**: every `base_stats` entry is a raw box-score column of the 001 contract.
2. **Shapes**: `category_values` returns shape (iterations, n_categories), and ratio categories
   equal Σ numerator / Σ denominator exactly.
3. **Zero attempts**: a zero denominator gives NaN, and `compare` treats NaN as a tie.
4. **Antisymmetry**: `compare(a, b) == -compare(b, a)`, and `compare(a, a) == 0`.
5. **Direction**: if team A beats B in a higher-is-better category and its values are then
   negated, `compare` flips. For the lower-is-better category, the lower total wins.
6. **Matchup range**: `matchup` returns values in {+1, 0, −1} and is antisymmetric.
7. **Ratio of means**: `projected_average` of ratio categories is the ratio of means, which differs
   from the mean of ratios on a constructed example.
8. **Unknown format**: `get_format("unknown")` raises `UnsupportedFormat`.
