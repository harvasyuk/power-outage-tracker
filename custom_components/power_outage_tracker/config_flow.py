"""Config flow for Power Outage Tracker."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_OUTAGE_DELAY,
    CONF_RESTORE_DELAY,
    CONF_SOURCE_ENTITY_1,
    CONF_SOURCE_ENTITY_2,
    CONF_STARTUP_GRACE,
    DEFAULT_OUTAGE_DELAY,
    DEFAULT_RESTORE_DELAY,
    DEFAULT_STARTUP_GRACE,
    DOMAIN,
    MAX_DELAY,
    MIN_DELAY,
)


def _entity_selector() -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain="switch"))


def _seconds_selector() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=MIN_DELAY,
            max=MAX_DELAY,
            step=1,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement="s",
        )
    )


def _source_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    values = defaults or {}
    name = values.get(CONF_NAME, "Grid power")
    primary = values.get(CONF_SOURCE_ENTITY_1)
    primary_marker = (
        vol.Required(CONF_SOURCE_ENTITY_1, default=primary)
        if primary
        else vol.Required(CONF_SOURCE_ENTITY_1)
    )
    schema: dict[vol.Marker, Any] = {
        vol.Required(CONF_NAME, default=name): str,
        primary_marker: _entity_selector(),
    }
    source_2 = values.get(CONF_SOURCE_ENTITY_2)
    optional_marker = (
        vol.Optional(CONF_SOURCE_ENTITY_2, default=source_2)
        if source_2
        else vol.Optional(CONF_SOURCE_ENTITY_2)
    )
    schema[optional_marker] = _entity_selector()
    return vol.Schema(schema)


def _delay_fields(defaults: dict[str, Any]) -> dict[vol.Marker, Any]:
    return {
        vol.Required(
            CONF_STARTUP_GRACE,
            default=defaults.get(CONF_STARTUP_GRACE, DEFAULT_STARTUP_GRACE),
        ): _seconds_selector(),
        vol.Required(
            CONF_OUTAGE_DELAY,
            default=defaults.get(CONF_OUTAGE_DELAY, DEFAULT_OUTAGE_DELAY),
        ): _seconds_selector(),
        vol.Required(
            CONF_RESTORE_DELAY,
            default=defaults.get(CONF_RESTORE_DELAY, DEFAULT_RESTORE_DELAY),
        ): _seconds_selector(),
    }


def _delay_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(_delay_fields(defaults))


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    primary = defaults.get(CONF_SOURCE_ENTITY_1)
    primary_marker = (
        vol.Required(CONF_SOURCE_ENTITY_1, default=primary)
        if primary
        else vol.Required(CONF_SOURCE_ENTITY_1)
    )
    source_2 = defaults.get(CONF_SOURCE_ENTITY_2)
    optional_marker = (
        vol.Optional(CONF_SOURCE_ENTITY_2, default=source_2)
        if source_2
        else vol.Optional(CONF_SOURCE_ENTITY_2)
    )
    return vol.Schema(
        {
            primary_marker: _entity_selector(),
            optional_marker: _entity_selector(),
            **_delay_fields(defaults),
        },
    )


def _validate_source_entities(data: dict[str, Any]) -> dict[str, str]:
    if data.get(CONF_SOURCE_ENTITY_2) == data[CONF_SOURCE_ENTITY_1]:
        return {CONF_SOURCE_ENTITY_2: "duplicate_source"}
    return {}


def _source_unique_id(data: dict[str, Any]) -> str:
    sources = [data[CONF_SOURCE_ENTITY_1]]
    if source_2 := data.get(CONF_SOURCE_ENTITY_2):
        sources.append(source_2)
    return "|".join(sorted(sources))


class PowerOutageTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect source entities."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            if not name or len(name) > 64:
                errors[CONF_NAME] = "invalid_name"
            errors.update(_validate_source_entities(user_input))
            if not errors:
                user_input[CONF_NAME] = name
                await self.async_set_unique_id(_source_unique_id(user_input))
                self._abort_if_unique_id_configured()
                self._source_data = user_input
                return await self.async_step_delays()

        return self.async_show_form(
            step_id="user",
            data_schema=_source_schema(user_input),
            errors=errors,
        )

    async def async_step_delays(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect confirmation delays."""
        if user_input is not None:
            data = {**self._source_data, **user_input}
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(
            step_id="delays",
            data_schema=_delay_schema({}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> PowerOutageTrackerOptionsFlow:
        """Return the options flow."""
        return PowerOutageTrackerOptionsFlow()


class PowerOutageTrackerOptionsFlow(config_entries.OptionsFlowWithReload):
    """Change source entities and confirmation timings."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage tracker settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_source_entities(user_input)
            unique_id = _source_unique_id(user_input)
            if any(
                entry.entry_id != self.config_entry.entry_id
                and entry.unique_id == unique_id
                for entry in self.hass.config_entries.async_entries(DOMAIN)
            ):
                errors["base"] = "already_configured"

            if not errors:
                settings = dict(user_input)
                if not settings.get(CONF_SOURCE_ENTITY_2):
                    settings.pop(CONF_SOURCE_ENTITY_2, None)

                data = {**self.config_entry.data, **settings}
                if CONF_SOURCE_ENTITY_2 not in settings:
                    data.pop(CONF_SOURCE_ENTITY_2, None)
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=data,
                    unique_id=unique_id,
                )
                return self.async_create_entry(data=settings)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(user_input or defaults),
            errors=errors,
        )
