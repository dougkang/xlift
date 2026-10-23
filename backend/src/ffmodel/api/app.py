"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ffmodel.api.routes import router
from ffmodel.contract.db import _repo_root, get_engine
from ffmodel.contract.migrate import migrate

DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def create_app(engine=None) -> FastAPI:
    engine = engine or get_engine()
    migrate(engine)
    app = FastAPI(title="FF-Model", version="0.1.0")
    app.state.engine = engine
    app.add_middleware(
        CORSMiddleware, allow_origins=DEV_ORIGINS, allow_methods=["*"], allow_headers=["*"]
    )
    app.include_router(router)
    dist = _repo_root() / "frontend" / "dist"
    if Path(dist).is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app
