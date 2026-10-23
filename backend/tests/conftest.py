import socket

import pytest


@pytest.fixture(autouse=True)
def _block_network(request, monkeypatch):
    """Tests never touch the network unless marked `live`."""
    if request.node.get_closest_marker("live"):
        return

    def guard(*args, **kwargs):
        raise RuntimeError("network disabled in tests")

    monkeypatch.setattr(socket.socket, "connect", guard)


@pytest.fixture
def engine(tmp_path):
    from ffmodel.contract.db import get_engine
    from ffmodel.contract.migrate import migrate

    eng = get_engine(f"sqlite:///{tmp_path}/t.sqlite")
    migrate(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def fixture_engine(engine):
    from tests.fixtures.dataset import load_fixture

    with engine.begin() as conn:
        load_fixture(conn)
    return engine
