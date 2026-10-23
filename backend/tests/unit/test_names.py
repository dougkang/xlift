import pytest

from ffmodel.contract.names import name_words, normalize_name


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Luka Dončić", "luka doncic"),
        ("Alperen Şengün", "alperen sengun"),
        ("Dennis Schröder", "dennis schroder"),
        ("Egor Dëmin", "egor demin"),
        ("Nikola Vučević", "nikola vucevic"),
        ("Jimmy Butler III", "jimmy butler"),
        ("Bobby Portis Jr.", "bobby portis"),
        ("N. Alexander-Walker", "n alexander walker"),
        ("Day'Ron Sharpe", "day ron sharpe"),
        ("Kel'el Ware", "kel el ware"),
        ("Kel’el Ware", "kel el ware"),
    ],
)
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


def test_name_words():
    assert name_words("  Lu  DON ") == ["lu", "don"]
