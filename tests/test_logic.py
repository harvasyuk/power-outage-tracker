"""Tests for source aggregation."""

import pytest

from custom_components.power_outage_tracker.logic import (
    AggregateCondition,
    SourceCondition,
    aggregate_source_states,
    classify_source_state,
)


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("on", SourceCondition.PRESENT),
        ("off", SourceCondition.PRESENT),
        ("idle", SourceCondition.PRESENT),
        ("unavailable", SourceCondition.UNAVAILABLE),
        ("unknown", SourceCondition.INDETERMINATE),
        (None, SourceCondition.INDETERMINATE),
    ],
)
def test_classify_source_state(
    state: str | None, expected: SourceCondition
) -> None:
    """Every normal state means the source is reachable."""
    assert classify_source_state(state) is expected


@pytest.mark.parametrize(
    ("states", "expected"),
    [
        (["on"], AggregateCondition.PRESENT),
        (["off"], AggregateCondition.PRESENT),
        (["unavailable"], AggregateCondition.OUTAGE),
        (["unknown"], AggregateCondition.INDETERMINATE),
        ([None], AggregateCondition.INDETERMINATE),
        (["on", "unavailable"], AggregateCondition.PRESENT),
        (["off", "unknown"], AggregateCondition.PRESENT),
        (["unavailable", "unavailable"], AggregateCondition.OUTAGE),
        (["unavailable", "unknown"], AggregateCondition.INDETERMINATE),
        (["unavailable", None], AggregateCondition.INDETERMINATE),
        (["unknown", "unknown"], AggregateCondition.INDETERMINATE),
        ([], AggregateCondition.INDETERMINATE),
    ],
)
def test_aggregate_source_states(
    states: list[str | None], expected: AggregateCondition
) -> None:
    """Any reachable source wins; outage requires all unavailable."""
    assert aggregate_source_states(states) is expected
