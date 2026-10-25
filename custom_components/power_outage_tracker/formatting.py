"""Localized human-readable formatting helpers."""

from __future__ import annotations

from datetime import datetime

UKRAINIAN_MONTHS = {
    1: "січ",
    2: "лют",
    3: "бер",
    4: "кві",
    5: "тра",
    6: "чер",
    7: "лип",
    8: "сер",
    9: "вер",
    10: "жов",
    11: "лис",
    12: "гру",
}

ENGLISH_MONTHS = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


def format_duration(seconds: float | None, language: str) -> str:
    """Format seconds as a compact localized duration."""
    if seconds is None:
        return "—"

    whole_seconds = max(0, int(seconds))
    days, remainder = divmod(whole_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60

    ukrainian = language.lower().startswith("uk")
    day_unit, hour_unit, minute_unit = (
        ("д", "г", "хв") if ukrainian else ("d", "h", "min")
    )

    parts: list[str] = []
    if days:
        parts.append(f"{days}{day_unit}")
    if hours:
        parts.append(f"{hours}{hour_unit}")
    parts.append(f"{minutes}{minute_unit}")
    return " ".join(parts)


def format_time(timestamp: datetime | None, now: datetime, language: str) -> str:
    """Format a timestamp with localized abbreviated month names."""
    if timestamp is None:
        return "—"

    time_text = timestamp.strftime("%H:%M")
    if (now - timestamp).total_seconds() < 86400:
        return time_text
    months = (
        UKRAINIAN_MONTHS
        if language.lower().startswith("uk")
        else ENGLISH_MONTHS
    )
    return f"{timestamp.day} {months[timestamp.month]} {time_text}"
