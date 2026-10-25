"""Tests for Power Outage Tracker configuration helpers."""

from custom_components.power_outage_tracker.config_flow import (
    _source_unique_id,
    _validate_source_entities,
)
from custom_components.power_outage_tracker.const import (
    CONF_SOURCE_ENTITY_1,
    CONF_SOURCE_ENTITY_2,
)


def test_source_unique_id_is_order_independent() -> None:
    """A two-plug tracker has the same identity regardless of plug order."""
    first = {
        CONF_SOURCE_ENTITY_1: "switch.socket_1",
        CONF_SOURCE_ENTITY_2: "switch.socket_2",
    }
    reversed_sources = {
        CONF_SOURCE_ENTITY_1: "switch.socket_2",
        CONF_SOURCE_ENTITY_2: "switch.socket_1",
    }

    assert _source_unique_id(first) == _source_unique_id(reversed_sources)


def test_duplicate_source_is_rejected() -> None:
    """The same switch cannot fill both source fields."""
    sources = {
        CONF_SOURCE_ENTITY_1: "switch.socket_1",
        CONF_SOURCE_ENTITY_2: "switch.socket_1",
    }

    assert _validate_source_entities(sources) == {
        CONF_SOURCE_ENTITY_2: "duplicate_source"
    }


def test_empty_secondary_source_is_allowed() -> None:
    """Clearing the optional source produces a valid single-source setup."""
    sources = {
        CONF_SOURCE_ENTITY_1: "switch.socket_1",
        CONF_SOURCE_ENTITY_2: "",
    }

    assert _validate_source_entities(sources) == {}
    assert _source_unique_id(sources) == "switch.socket_1"
