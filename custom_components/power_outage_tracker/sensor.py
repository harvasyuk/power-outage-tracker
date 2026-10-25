"""Sensor platform for Power Outage Tracker."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import MONITORING_STATUSES, STATE_POWER_OUTAGE, STATE_POWER_PRESENT
from .coordinator import PowerOutageCoordinator
from .entity import PowerOutageTrackerEntity
from .formatting import format_duration, format_time

SensorValue = str | float | datetime | None


@dataclass(frozen=True, kw_only=True)
class TrackerSensorDescription(SensorEntityDescription):
    """Describe a tracker sensor."""

    value_fn: Callable[[PowerOutageCoordinator], SensorValue]


SENSOR_DESCRIPTIONS = (
    TrackerSensorDescription(
        key="monitoring_status",
        translation_key="monitoring_status",
        device_class=SensorDeviceClass.ENUM,
        options=MONITORING_STATUSES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: coordinator.monitoring_status,
    ),
    TrackerSensorDescription(
        key="current_period_duration",
        translation_key="current_period_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_display_precision=0,
        value_fn=lambda coordinator: coordinator.current_duration(),
    ),
    TrackerSensorDescription(
        key="current_period_started",
        translation_key="current_period_started",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda coordinator: coordinator.state.current_period_started_at,
    ),
    TrackerSensorDescription(
        key="last_outage_duration",
        translation_key="last_outage_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_display_precision=0,
        value_fn=lambda coordinator: coordinator.state.last_outage.duration,
    ),
    TrackerSensorDescription(
        key="last_outage_started",
        translation_key="last_outage_started",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda coordinator: coordinator.most_recent_outage_start(),
    ),
    TrackerSensorDescription(
        key="last_power_duration",
        translation_key="last_power_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_display_precision=0,
        value_fn=lambda coordinator: coordinator.state.last_power.duration,
    ),
    TrackerSensorDescription(
        key="last_power_started",
        translation_key="last_power_started",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda coordinator: coordinator.most_recent_power_start(),
    ),
    TrackerSensorDescription(
        key="power_duration_display",
        translation_key="power_duration_display",
        value_fn=lambda coordinator: format_duration(
            coordinator.current_duration()
            if coordinator.state.confirmed_state == STATE_POWER_PRESENT
            else coordinator.state.last_power.duration,
            coordinator.hass.config.language,
        ),
    ),
    TrackerSensorDescription(
        key="outage_duration_display",
        translation_key="outage_duration_display",
        value_fn=lambda coordinator: format_duration(
            coordinator.current_duration()
            if coordinator.state.confirmed_state == STATE_POWER_OUTAGE
            else coordinator.state.last_outage.duration,
            coordinator.hass.config.language,
        ),
    ),
    TrackerSensorDescription(
        key="power_time_display",
        translation_key="power_time_display",
        value_fn=lambda coordinator: format_time(
            dt_util.as_local(coordinator.most_recent_power_start())
            if coordinator.most_recent_power_start()
            else None,
            dt_util.as_local(dt_util.utcnow()),
            coordinator.hass.config.language,
        ),
    ),
    TrackerSensorDescription(
        key="outage_time_display",
        translation_key="outage_time_display",
        value_fn=lambda coordinator: format_time(
            dt_util.as_local(coordinator.most_recent_outage_start())
            if coordinator.most_recent_outage_start()
            else None,
            dt_util.as_local(dt_util.utcnow()),
            coordinator.hass.config.language,
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up tracker sensors."""
    async_add_entities(
        TrackerSensor(entry.runtime_data, description)
        for description in SENSOR_DESCRIPTIONS
    )


class TrackerSensor(PowerOutageTrackerEntity, SensorEntity):
    """A sensor backed by tracker state."""

    entity_description: TrackerSensorDescription

    def __init__(
        self,
        coordinator: PowerOutageCoordinator,
        description: TrackerSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> SensorValue:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def icon(self) -> str | None:
        """Distinguish the current power or outage period visually."""
        if self.entity_description.key == "current_period_duration":
            if self.coordinator.state.confirmed_state == STATE_POWER_PRESENT:
                return "mdi:timer-sand-full"
            if self.coordinator.state.confirmed_state == STATE_POWER_OUTAGE:
                return "mdi:timer-sand-empty"
        if self.entity_description.key == "current_period_started":
            if self.coordinator.state.confirmed_state == STATE_POWER_PRESENT:
                return "mdi:clock"
            if self.coordinator.state.confirmed_state == STATE_POWER_OUTAGE:
                return "mdi:clock-outline"
        return super().icon

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Add context to period timestamp sensors."""
        if self.entity_description.key == "current_period_started":
            return {
                "estimated_start": self.coordinator.state.current_start_estimated,
                "confirmed_state": self.coordinator.state.confirmed_state,
            }
        if self.entity_description.key == "last_outage_started":
            estimated = (
                self.coordinator.state.current_start_estimated
                if self.coordinator.state.confirmed_state == STATE_POWER_OUTAGE
                else self.coordinator.state.last_outage.estimated_start
            )
            return {"estimated_start": estimated}
        if self.entity_description.key == "last_power_started":
            estimated = (
                self.coordinator.state.current_start_estimated
                if self.coordinator.state.confirmed_state == STATE_POWER_PRESENT
                else self.coordinator.state.last_power.estimated_start
            )
            return {"estimated_start": estimated}
        return None
