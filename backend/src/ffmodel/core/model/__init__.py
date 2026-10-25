"""Player model. `fit` is database-free; `build_projections` reads the data contract and is
loaded lazily so importing the model (e.g. from the simulation engine) never pulls in the DB."""

from ffmodel.core.model.fit import (
    MeanPrior,
    PlayerProjection,
    RatioPrior,
    availability_rate,
    estimate_prior,
    fit_projection,
    shrink_projection,
)

__all__ = [
    "MeanPrior",
    "PlayerProjection",
    "RatioPrior",
    "availability_rate",
    "build_prior",
    "build_projections",
    "estimate_prior",
    "fit_projection",
    "prior_pool_windows",
    "shrink_projection",
]


def __getattr__(name: str):
    if name in ("build_projections", "build_prior", "prior_pool_windows"):
        from ffmodel.core.model import projection

        return getattr(projection, name)
    raise AttributeError(name)
