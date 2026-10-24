"""Kernel density curves for display (research R6). Display only; statistics use all samples."""

from collections.abc import Mapping

import numpy as np


def density_curves(
    samples_by_role: Mapping[str, np.ndarray],
    *,
    points: int = 96,
    subsample: int = 2000,
    seed: int = 0,
) -> dict:
    rng = np.random.default_rng(seed)
    clean = {}
    for role, values in samples_by_role.items():
        v = np.asarray(values, dtype=float)
        v = v[np.isfinite(v)]
        if v.size > subsample:
            v = rng.choice(v, subsample, replace=False)
        clean[role] = v
    nonempty = [v for v in clean.values() if v.size]
    pooled = np.concatenate(nonempty) if nonempty else np.array([])
    if pooled.size == 0:
        return {"x": [], "series": {role: [] for role in clean}}
    lo, hi = np.percentile(pooled, [0.5, 99.5])
    for v in clean.values():
        if v.size:
            lo, hi = min(lo, float(np.median(v))), max(hi, float(np.median(v)))
    if hi - lo < 1e-9:
        lo, hi = lo - 0.5, hi + 0.5
    x = np.linspace(lo, hi, points)
    series = {}
    for role, v in clean.items():
        if v.size == 0:
            series[role] = np.zeros(points)
            continue
        sd = float(np.std(v))
        bw = 1.06 * sd * v.size ** (-1 / 5) if sd > 0 else (hi - lo) / points
        z = (x[:, None] - v[None, :]) / bw
        dens = np.exp(-0.5 * z * z).sum(axis=1) / (v.size * bw * np.sqrt(2 * np.pi))
        series[role] = dens
    return {"x": x, "series": series}
