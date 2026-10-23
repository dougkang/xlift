"""NBA season labels (e.g. 2026-27). The new season label starts in October."""

from datetime import date


def season_label(start_year: int) -> str:
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def current_season(today: date) -> str:
    return season_label(today.year if today.month >= 10 else today.year - 1)


def previous_season(season: str) -> str:
    return season_label(int(season[:4]) - 1)
