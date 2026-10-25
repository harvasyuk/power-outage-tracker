"""Tests for persistent tracker state."""

from datetime import UTC, datetime

from custom_components.power_outage_tracker.const import STATE_POWER_PRESENT
from custom_components.power_outage_tracker.models import (
    CompletedPeriod,
    TrackerState,
)


def test_state_round_trip() -> None:
    """Stored state round-trips without losing timestamps or durations."""
    start = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
    end = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
    original = TrackerState(
        confirmed_state=STATE_POWER_PRESENT,
        current_period_started_at=end,
        current_start_estimated=False,
        last_outage=CompletedPeriod(start, end, 3600, True),
        last_source_observation_at=end,
    )

    restored = TrackerState.from_dict(original.as_dict())

    assert restored == original


def test_corrupt_state_is_not_confirmed() -> None:
    """Invalid stored data falls back to an uninitialized tracker."""
    restored = TrackerState.from_dict(
        {
            "confirmed_state": "broken",
            "current_period_started_at": "not-a-date",
            "last_outage": {"duration": -50},
        }
    )

    assert restored.confirmed_state is None
    assert restored.current_period_started_at is None
    assert restored.last_outage is not None
    assert restored.last_outage.duration == 0


def test_legacy_power_period_key_is_migrated() -> None:
    """Read the pre-0.1.3 storage key without losing its period."""
    restored = TrackerState.from_dict(
        {
            "last_power_present": {
                "started_at": "2026-10-25T08:00:00+00:00",
                "ended_at": "2026-10-25T09:00:00+00:00",
                "duration": 3600,
                "estimated_start": False,
            }
        }
    )

    assert restored.last_power.duration == 3600
    assert "last_power" in restored.as_dict()
    assert "last_power_present" not in restored.as_dict()
