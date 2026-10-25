"""Pure source-state aggregation logic."""

from __future__ import annotations

from enum import StrEnum
from typing import Iterable


class SourceCondition(StrEnum):
    """Meaning of a source entity state."""

    PRESENT = "present"
    UNAVAILABLE = "unavailable"
    INDETERMINATE = "indeterminate"


class AggregateCondition(StrEnum):
    """Combined meaning of all configured source states."""

    PRESENT = "present"
    OUTAGE = "outage"
    INDETERMINATE = "indeterminate"


def classify_source_state(state: str | None) -> SourceCondition:
    """Classify one source.

    Every real state, including "on" and "off", proves the device is reachable.
    A missing entity and "unknown" provide no evidence in either direction.
    """
    if state is None or state == "unknown":
        return SourceCondition.INDETERMINATE
    if state == "unavailable":
        return SourceCondition.UNAVAILABLE
    return SourceCondition.PRESENT


def aggregate_source_states(states: Iterable[str | None]) -> AggregateCondition:
    """Combine one or two source states conservatively."""
    conditions = [classify_source_state(state) for state in states]
    if not conditions:
        return AggregateCondition.INDETERMINATE
    if SourceCondition.PRESENT in conditions:
        return AggregateCondition.PRESENT
    if all(condition is SourceCondition.UNAVAILABLE for condition in conditions):
        return AggregateCondition.OUTAGE
    return AggregateCondition.INDETERMINATE
