"""Shared entity base for Power Outage Tracker."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN
from .coordinator import PowerOutageCoordinator


class PowerOutageTrackerEntity(Entity):
    """Base entity updated by the tracker coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PowerOutageCoordinator, key: str) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.name,
            manufacturer="Power Outage Tracker",
            model="Availability monitor",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._async_coordinator_updated)
        )

    def _async_coordinator_updated(self) -> None:
        self.async_write_ha_state()
