"""Binary sensor platform for Power Outage Tracker."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import STATE_POWER_OUTAGE, STATE_POWER_PRESENT
from .coordinator import PowerOutageCoordinator
from .entity import PowerOutageTrackerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the grid-power binary sensor."""
    async_add_entities([GridPowerBinarySensor(entry.runtime_data)])


class GridPowerBinarySensor(PowerOutageTrackerEntity, BinarySensorEntity):
    """Last confirmed grid power state."""

    _attr_device_class = BinarySensorDeviceClass.POWER
    _attr_translation_key = "grid_power"

    def __init__(self, coordinator: PowerOutageCoordinator) -> None:
        super().__init__(coordinator, "grid_power")

    @property
    def is_on(self) -> bool | None:
        """Return whether grid power is confirmed present."""
        if self.coordinator.state.confirmed_state == STATE_POWER_PRESENT:
            return True
        if self.coordinator.state.confirmed_state == STATE_POWER_OUTAGE:
            return False
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose source diagnostics."""
        return self.coordinator.source_state_attributes
