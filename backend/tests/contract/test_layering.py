import shutil
import subprocess
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]


def test_import_layering_contracts():
    exe = shutil.which("lint-imports")
    assert exe, "lint-imports not installed (uv sync --group dev)"
    result = subprocess.run([exe], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
