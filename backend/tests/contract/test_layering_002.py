"""Constitution VII: the modeling core's math (scoring, fit, simulation) is database-free."""

import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module",
    ["ffmodel.core.sim", "ffmodel.core.scoring", "ffmodel.core.model", "ffmodel.core.scenario"],
)
def test_imports_without_database_layer(module):
    code = f"import sys, {module}; assert 'sqlalchemy' not in sys.modules, 'sqlalchemy loaded'"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_build_projections_still_available_lazily():
    from ffmodel.core.model import build_projections

    assert callable(build_projections)
