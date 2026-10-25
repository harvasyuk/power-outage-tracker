"""Runtime data models for Power Outage Tracker."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .const import STATE_POWER_OUTAGE, STATE_POWER_PRESENT


def _parse_datetime(value: Any) -> datetime | None:
    """Parse a stored ISO timestamp, returning None for invalid data."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _duration(value: Any) -> float | None:
    """Parse a non-negative stored duration."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    return max(0.0, float(value))


@dataclass(slots=True)
class CompletedPeriod:
    """One most recently completed period of a given type."""

    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration: float | None = None
    estimated_start: bool = False

    @classmethod
    def from_dict(cls, data: Any) -> CompletedPeriod:
        """Deserialize safely."""
        if not isinstance(data, dict):
            return cls()
        return cls(
            started_at=_parse_datetime(data.get("started_at")),
            ended_at=_parse_datetime(data.get("ended_at")),
            duration=_duration(data.get("duration")),
            estimated_start=bool(data.get("estimated_start", False)),
        )

    def as_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible data."""
        return {
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration": self.duration,
            "estimated_start": self.estimated_start,
        }


@dataclass(slots=True)
class TrackerState:
    """Persistent tracker state."""

    confirmed_state: str | None = None
    current_period_started_at: datetime | None = None
    current_start_estimated: bool = False
    last_outage: CompletedPeriod = field(default_factory=CompletedPeriod)
    last_power: CompletedPeriod = field(default_factory=CompletedPeriod)
    last_source_observation_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: Any) -> TrackerState:
        """Deserialize safely and ignore corrupt state."""
        if not isinstance(data, dict):
            return cls()
        confirmed_state = data.get("confirmed_state")
        if confirmed_state not in (STATE_POWER_PRESENT, STATE_POWER_OUTAGE):
            confirmed_state = None
        started_at = _parse_datetime(data.get("current_period_started_at"))
        if confirmed_state is None or started_at is None:
            confirmed_state = None
            started_at = None
        return cls(
            confirmed_state=confirmed_state,
            current_period_started_at=started_at,
            current_start_estimated=bool(data.get("current_start_estimated", False)),
            last_outage=CompletedPeriod.from_dict(data.get("last_outage")),
            last_power=CompletedPeriod.from_dict(
                data.get("last_power", data.get("last_power_present"))
            ),
            last_source_observation_at=_parse_datetime(
                data.get("last_source_observation_at")
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible data."""
        return {
            "confirmed_state": self.confirmed_state,
            "current_period_started_at": (
                self.current_period_started_at.isoformat()
                if self.current_period_started_at
                else None
            ),
            "current_start_estimated": self.current_start_estimated,
            "last_outage": self.last_outage.as_dict(),
            "last_power": self.last_power.as_dict(),
            "last_source_observation_at": (
                self.last_source_observation_at.isoformat()
                if self.last_source_observation_at
                else None
            ),
        }
