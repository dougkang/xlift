"""The Fragility Penalty. Moved to `ffmodel.core.model.fragility` so every tool shares it (009
research R1); re-exported here for Impact Analysis's callers."""

from ffmodel.core.model.fragility import apply, dab_values

__all__ = ["apply", "dab_values"]
