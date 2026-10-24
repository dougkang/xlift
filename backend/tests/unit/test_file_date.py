"""As-of dates inferred from export files (005): captures before noon describe the day before."""

import os
from datetime import date, datetime

import pytest

from ffmodel.adapters.common import file_date


@pytest.mark.parametrize(
    "modified,expected",
    [
        (datetime(2026, 10, 24, 0, 7), date(2026, 10, 23)),  # just after midnight
        (datetime(2026, 10, 24, 11, 59), date(2026, 10, 23)),
        (datetime(2026, 10, 24, 12, 0), date(2026, 10, 24)),  # noon and later: same day
        (datetime(2026, 10, 23, 23, 19), date(2026, 10, 23)),
    ],
)
def test_noon_cutoff(tmp_path, modified, expected):
    p = tmp_path / "export.csv"
    p.write_text("x\n")
    os.utime(p, (modified.timestamp(), modified.timestamp()))
    assert file_date(p) == expected
