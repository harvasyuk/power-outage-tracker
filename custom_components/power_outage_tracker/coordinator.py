"""Power outage state machine and persistence."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_OUTAGE_DELAY,
    CONF_RESTORE_DELAY,
    CONF_SOURCE_ENTITY_1,
    CONF_SOURCE_ENTITY_2,
    CONF_STARTUP_GRACE,
    DEFAULT_OUTAGE_DELAY,
    DEFAULT_RESTORE_DELAY,
    DEFAULT_STARTUP_GRACE,
    EVENT_OUTAGE_STARTED,
    EVENT_POWER_RESTORED,
    STATE_POWER_OUTAGE,
    STATE_POWER_PRESENT,
    STATUS_POSSIBLE_OUTAGE,
    STATUS_POSSIBLE_RESTORE,
    STATUS_STARTING,
    STATUS_TRACKING,
    STATUS_WAITING_FOR_SOURCE,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
    UPDATE_INTERVAL,
)
from .logic import AggregateCondition, aggregate_source_states
from .models import CompletedPeriod, TrackerState

_LOGGER = logging.getLogger(__name__)

Listener = Callable[[], None]


class PowerOutageCoordinator:
    """Track source availability and expose a confirmed grid state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        settings = {**entry.data, **entry.options}
        self.name: str = entry.title
        self.source_entity_ids = [settings[CONF_SOURCE_ENTITY_1]]
        if source_2 := settings.get(CONF_SOURCE_ENTITY_2):
            self.source_entity_ids.append(source_2)
        self.startup_grace = int(
            settings.get(CONF_STARTUP_GRACE, DEFAULT_STARTUP_GRACE)
        )
        self.outage_delay = int(
            settings.get(CONF_OUTAGE_DELAY, DEFAULT_OUTAGE_DELAY)
        )
        self.restore_delay = int(
            settings.get(CONF_RESTORE_DELAY, DEFAULT_RESTORE_DELAY)
        )

        self.state = TrackerState()
        self.monitoring_status = STATUS_STARTING
        self.source_states: dict[str, str | None] = {}
        self.aggregate_condition = AggregateCondition.INDETERMINATE
        self.aggregate_since = dt_util.utcnow()

        self._store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY_PREFIX}.{entry.entry_id}",
        )
        self._listeners: set[Listener] = set()
        self._unsubscribers: list[Callable[[], None]] = []
        self._cancel_candidate: Callable[[], None] | None = None
        self._candidate_condition: AggregateCondition | None = None
        self._startup_active = True
        self._evidence_gap = False
        self._lock = asyncio.Lock()
        self._closed = False

    async def async_setup(self) -> None:
        """Restore state, subscribe to sources, and begin startup guard."""
        stored = await self._store.async_load()
        self.state = TrackerState.from_dict(stored)

        now = dt_util.utcnow()
        self.source_states = {
            entity_id: (
                source_state.state
                if (source_state := self.hass.states.get(entity_id))
                else None
            )
            for entity_id in self.source_entity_ids
        }
        self.aggregate_condition = aggregate_source_states(
            self.source_states.values()
        )
        self.aggregate_since = now
        self.state.last_source_observation_at = now

        self._unsubscribers.append(
            async_track_state_change_event(
                self.hass, self.source_entity_ids, self._async_source_event
            )
        )
        self._unsubscribers.append(
            async_track_time_interval(
                self.hass, self._async_minute_tick, UPDATE_INTERVAL
            )
        )

        if self.hass.is_running:
            await self._async_begin_startup_grace()
        else:
            self._unsubscribers.append(
                self.hass.bus.async_listen_once(
                    EVENT_HOMEASSISTANT_STARTED, self._async_home_assistant_started
                )
            )

    async def async_shutdown(self) -> None:
        """Stop listeners and persist the latest confirmed state."""
        self._closed = True
        self._cancel_pending_candidate()
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        await self._async_save()

    @callback
    def async_add_listener(self, listener: Listener) -> Callable[[], None]:
        """Subscribe an entity to coordinator updates."""
        self._listeners.add(listener)

        @callback
        def unsubscribe() -> None:
            self._listeners.discard(listener)

        return unsubscribe

    @callback
    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    @callback
    def _async_source_event(self, event: Event[EventStateChangedData]) -> None:
        """Queue source processing without blocking the event bus."""
        self.hass.async_create_task(self._async_process_source_event(event))

    async def _async_process_source_event(
        self, event: Event[EventStateChangedData]
    ) -> None:
        async with self._lock:
            if self._closed:
                return
            entity_id = event.data["entity_id"]
            new_state = event.data["new_state"]
            raw_state = new_state.state if new_state is not None else None
            if self.source_states.get(entity_id) == raw_state:
                return

            now = dt_util.utcnow()
            self.source_states[entity_id] = raw_state
            self.state.last_source_observation_at = now
            new_aggregate = aggregate_source_states(self.source_states.values())
            if new_aggregate is not self.aggregate_condition:
                self.aggregate_condition = new_aggregate
                self.aggregate_since = now

            if self._startup_active:
                self.monitoring_status = STATUS_STARTING
                self._notify_listeners()
                return
            await self._async_evaluate(now)

    @callback
    def _async_home_assistant_started(self, _event: Event) -> None:
        """Begin the grace period only after Home Assistant is running."""
        self.hass.async_create_task(self._async_begin_startup_grace())

    async def _async_begin_startup_grace(self) -> None:
        """Start or immediately complete the post-start grace period."""
        if self._closed or not self._startup_active:
            return
        if self.startup_grace == 0:
            await self._async_finish_startup()
            return
        self._unsubscribers.append(
            async_call_later(
                self.hass,
                self.startup_grace,
                self._async_startup_timer,
            )
        )

    @callback
    def _async_startup_timer(self, _now: datetime) -> None:
        self.hass.async_create_task(self._async_finish_startup())

    async def _async_finish_startup(self) -> None:
        async with self._lock:
            if self._closed or not self._startup_active:
                return
            self._startup_active = False
            await self._async_evaluate(dt_util.utcnow(), startup_evaluation=True)

    @callback
    def _async_minute_tick(self, _now: datetime) -> None:
        """Refresh live duration entities."""
        if not self._closed:
            self._notify_listeners()

    async def _async_evaluate(
        self, now: datetime, *, startup_evaluation: bool = False
    ) -> None:
        """Evaluate the aggregate condition against the confirmed state."""
        condition = self.aggregate_condition
        confirmed = self.state.confirmed_state

        if condition is AggregateCondition.INDETERMINATE:
            self._cancel_pending_candidate()
            self._evidence_gap = True
            self.monitoring_status = STATUS_WAITING_FOR_SOURCE
            self._notify_listeners()
            return

        if confirmed is None:
            if condition is AggregateCondition.PRESENT:
                await self._async_confirm_initial(
                    STATE_POWER_PRESENT, self.aggregate_since, estimated=True
                )
            else:
                self._begin_candidate(
                    condition,
                    now,
                    self.outage_delay,
                    STATUS_POSSIBLE_OUTAGE,
                    estimated=True,
                )
            return

        expected = (
            AggregateCondition.PRESENT
            if confirmed == STATE_POWER_PRESENT
            else AggregateCondition.OUTAGE
        )
        if condition is expected:
            self._cancel_pending_candidate()
            self._evidence_gap = False
            self.monitoring_status = STATUS_TRACKING
            self._notify_listeners()
            return

        if confirmed == STATE_POWER_PRESENT:
            self._begin_candidate(
                AggregateCondition.OUTAGE,
                now,
                self.outage_delay,
                STATUS_POSSIBLE_OUTAGE,
                estimated=startup_evaluation or self._evidence_gap,
            )
        else:
            self._begin_candidate(
                AggregateCondition.PRESENT,
                now,
                self.restore_delay,
                STATUS_POSSIBLE_RESTORE,
                estimated=startup_evaluation or self._evidence_gap,
            )

    def _begin_candidate(
        self,
        condition: AggregateCondition,
        now: datetime,
        delay_seconds: int,
        status: str,
        *,
        estimated: bool,
    ) -> None:
        """Start a confirmation timer, accounting for time already stable."""
        if self._candidate_condition is condition:
            return
        self._cancel_pending_candidate()
        self._candidate_condition = condition
        self.monitoring_status = status
        self._notify_listeners()

        stable_for = max(0.0, (now - self.aggregate_since).total_seconds())
        remaining = max(0.0, delay_seconds - stable_for)

        if remaining == 0:
            self.hass.async_create_task(
                self._async_candidate_elapsed(condition, estimated)
            )
            return

        @callback
        def candidate_timer(_timer_now: datetime) -> None:
            self.hass.async_create_task(
                self._async_candidate_elapsed(condition, estimated)
            )

        self._cancel_candidate = async_call_later(
            self.hass, remaining, candidate_timer
        )

    async def _async_candidate_elapsed(
        self, condition: AggregateCondition, estimated: bool
    ) -> None:
        async with self._lock:
            if (
                self._closed
                or self._startup_active
                or self._candidate_condition is not condition
                or self.aggregate_condition is not condition
            ):
                return
            self._cancel_candidate = None
            self._candidate_condition = None
            new_state = (
                STATE_POWER_OUTAGE
                if condition is AggregateCondition.OUTAGE
                else STATE_POWER_PRESENT
            )
            if self.state.confirmed_state is None:
                await self._async_confirm_initial(
                    new_state, self.aggregate_since, estimated=True
                )
            else:
                await self._async_transition(
                    new_state, self.aggregate_since, estimated=estimated
                )

    @callback
    def _cancel_pending_candidate(self) -> None:
        if self._cancel_candidate is not None:
            self._cancel_candidate()
            self._cancel_candidate = None
        self._candidate_condition = None

    async def _async_confirm_initial(
        self, state: str, started_at: datetime, *, estimated: bool
    ) -> None:
        self.state.confirmed_state = state
        self.state.current_period_started_at = started_at
        self.state.current_start_estimated = estimated
        self._evidence_gap = False
        self.monitoring_status = STATUS_TRACKING
        await self._async_save()
        self._notify_listeners()

    async def _async_transition(
        self, new_state: str, started_at: datetime, *, estimated: bool
    ) -> None:
        old_state = self.state.confirmed_state
        old_started_at = self.state.current_period_started_at
        if old_state == new_state or old_state is None or old_started_at is None:
            return

        duration = max(0.0, (started_at - old_started_at).total_seconds())
        completed = CompletedPeriod(
            started_at=old_started_at,
            ended_at=started_at,
            duration=duration,
            estimated_start=self.state.current_start_estimated,
        )
        if old_state == STATE_POWER_PRESENT:
            self.state.last_power = completed
            event_type = EVENT_OUTAGE_STARTED
        else:
            self.state.last_outage = completed
            event_type = EVENT_POWER_RESTORED

        self.state.confirmed_state = new_state
        self.state.current_period_started_at = started_at
        self.state.current_start_estimated = estimated
        self._evidence_gap = False
        self.monitoring_status = STATUS_TRACKING
        await self._async_save()

        self.hass.bus.async_fire(
            event_type,
            {
                "config_entry_id": self.entry.entry_id,
                "name": self.name,
                "source_entities": self.source_entity_ids,
                "started_at": started_at.isoformat(),
                "previous_period_duration": duration,
                "estimated_start": estimated,
            },
        )
        self._notify_listeners()

    async def _async_save(self) -> None:
        try:
            await self._store.async_save(self.state.as_dict())
        except (OSError, TypeError, ValueError):
            _LOGGER.exception("Failed to save state for %s", self.name)

    def current_duration(self, now: datetime | None = None) -> float | None:
        """Return the current confirmed period duration in seconds."""
        if self.state.current_period_started_at is None:
            return None
        current_time = now or dt_util.utcnow()
        return max(
            0.0,
            (current_time - self.state.current_period_started_at).total_seconds(),
        )

    def most_recent_outage_start(self) -> datetime | None:
        """Return the current or most recently completed outage start."""
        if self.state.confirmed_state == STATE_POWER_OUTAGE:
            return self.state.current_period_started_at
        return self.state.last_outage.started_at

    def most_recent_power_start(self) -> datetime | None:
        """Return the current or most recently completed power period start."""
        if self.state.confirmed_state == STATE_POWER_PRESENT:
            return self.state.current_period_started_at
        return self.state.last_power.started_at

    @property
    def source_state_attributes(self) -> dict[str, Any]:
        """Return useful diagnostics for entity attributes."""
        return {
            "source_entities": self.source_entity_ids,
            "source_states": {
                entity_id: state if state is not None else "missing"
                for entity_id, state in self.source_states.items()
            },
            "aggregate_condition": self.aggregate_condition,
            "last_source_observation_at": self.state.last_source_observation_at,
            "current_period_start_estimated": self.state.current_start_estimated,
        }
