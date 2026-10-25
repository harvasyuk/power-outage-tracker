"""Tests for Ukrainian display formatting."""

from datetime import UTC, datetime

from custom_components.power_outage_tracker.formatting import (
    format_duration,
    format_time,
)


def test_format_duration() -> None:
    """Durations omit empty larger units and always include minutes."""
    assert format_duration(None, "uk") == "—"
    assert format_duration(45, "uk") == "0хв"
    assert format_duration(8040, "uk") == "2г 14хв"
    assert format_duration(108180, "uk") == "1д 6г 3хв"
    assert format_duration(108180, "en") == "1d 6h 3min"


def test_format_recent_ukrainian_time() -> None:
    """Recent times show only hours and minutes."""
    timestamp = datetime(2026, 10, 25, 14, 32, tzinfo=UTC)
    now = datetime(2026, 10, 25, 18, 0, tzinfo=UTC)
    assert format_time(timestamp, now, "uk") == "14:32"


def test_format_older_ukrainian_time() -> None:
    """Older times include a Ukrainian abbreviated month."""
    timestamp = datetime(2026, 10, 24, 14, 32, tzinfo=UTC)
    now = datetime(2026, 10, 25, 18, 0, tzinfo=UTC)
    assert format_time(timestamp, now, "uk") == "24 жов 14:32"
    assert format_time(timestamp, now, "en") == "24 Oct 14:32"
