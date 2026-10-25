# Power Outage Tracker

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Power Outage Tracker is a Home Assistant custom integration that creates a
virtual grid-monitoring device and infers grid power from the availability of
one or two smart plugs. It is designed to avoid false outage records while Home
Assistant and source integrations are starting.

## How detection works

- Any normal plug state, including `on` or `off`, proves power is present.
- An outage is possible only when every configured plug is `unavailable`.
- `unknown` or a missing entity is indeterminate and preserves the last
  confirmed grid state.
- Startup, outage, and restoration confirmation delays reject transient states.
- Confirmed state and period data are kept in Home Assistant's `.storage`
  directory and survive restarts.

With two sources, an unavailable plug does not indicate an outage while the
other plug remains reachable. Manually disconnecting every configured plug is
indistinguishable from a real outage.

## Installation

### HACS

1. Add `https://github.com/harvasyuk/power-outage-tracker` to HACS as a custom
   **Integration** repository.
2. Install **Power Outage Tracker**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/power_outage_tracker` into your Home Assistant
`custom_components` directory and restart Home Assistant.

## Configuration

Go to **Settings → Devices & services → Add integration**, search for
**Power Outage Tracker**, and choose:

- A tracker name.
- One required smart-plug switch entity.
- One optional second smart-plug switch entity.
- Startup grace period (default: 120 seconds).
- Outage confirmation delay (default: 60 seconds).
- Restoration confirmation delay (default: 15 seconds).

Source entities and timing values can be changed later from the integration's
**Configure** dialog. Clear the secondary smart-plug field to return to a
single-source tracker. Changing sources reloads the tracker but keeps its
persisted period history.

## Entities

Each tracker creates one device containing:

- **Grid power**: last confirmed power state.
- **Monitoring status**: starting, tracking, possible outage, possible
  restoration, or waiting for source.
- **Current period duration** and **Current period started**.
- **Last outage duration** and **Last outage started**.
- **Last power duration** and **Last power started**.
- **Power duration** and **Outage duration**: dashboard-oriented localized
  values such as `2h 14min`, or `2г 14хв` when Home Assistant is configured in
  Ukrainian. The active type updates live; the inactive type shows its most
  recently completed duration.
- **Power time** and **Outage time**: `HH:MM` for the last 24 hours, otherwise
  `D Mon HH:MM` using localized abbreviated month names.

Before the first relevant period exists, its value is `unknown` rather than
zero. Durations refresh once per minute and at confirmed transitions.

The Grid power entity has diagnostic attributes containing the individual
source states, combined condition, last observation time, and whether the
current period's start time is estimated.

## Startup and persistence

During the startup grace period, source changes cannot produce transitions.
After the grace period:

- A normal source confirms or retains power present.
- All sources continuously unavailable begin or continue outage confirmation.
- Any indeterminate source, when no source is normal, cancels a pending
  transition and leaves the persisted confirmed state unchanged.

If Home Assistant was not running when power changed, the exact transition
time cannot be recovered. Such a first post-start transition is marked as
estimated.

Home Assistant Recorder stores entity history according to the user's Recorder
retention settings. The integration itself stores only the active period and
the most recently completed outage and power periods.

## Development

Install the optional test dependencies and run:

```bash
pytest
ruff check .
```
