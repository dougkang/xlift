"""Player model. `fit` is database-free; `build_projections` reads the data contract and is
loaded lazily so importing the model (e.g. from the simulation engine) never pulls in the DB."""

from ffmodel.core.model.fit import PlayerProjection, availability_rate, fit_projection

__all__ = ["PlayerProjection", "availability_rate", "build_projections", "fit_projection"]


def __getattr__(name: str):
    if name == "build_projections":
        from ffmodel.core.model.projection import build_projections

        return build_projections
    raise AttributeError(name)
