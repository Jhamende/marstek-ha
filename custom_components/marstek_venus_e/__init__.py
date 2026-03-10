"""Marstek Venus E — Home Assistant custom integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv

from .api import MarsktekAPI
from .const import (
    ATTR_CD_TIME,
    ATTR_DEVICE_ID,
    ATTR_ENABLE,
    ATTR_END_TIME,
    ATTR_POWER,
    ATTR_START_TIME,
    ATTR_TIME_NUM,
    ATTR_WEEK_SET,
    CONF_DEVICE_LABEL,
    CONF_MAC,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SERVICE_CLEAR_SCHEDULES,
    SERVICE_FORCE_REFRESH,
    SERVICE_SET_MANUAL_SCHEDULE,
    SERVICE_SET_PASSIVE_MODE,
    WEEK_ALL_DAYS,
)
from .coordinator import MarsktekCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Marstek Venus E from a config entry."""
    host  = entry.data[CONF_HOST]
    port  = entry.data.get(CONF_PORT, DEFAULT_PORT)
    label = entry.data.get(CONF_DEVICE_LABEL, f"Marstek {host}")
    interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    api = MarsktekAPI(host, port)
    await api.connect()

    coordinator = MarsktekCoordinator(hass, api, label, scan_interval=interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator: MarsktekCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.api.close()
    return unloaded


# ── Service registration ──────────────────────────────────────────────────────

def _get_coordinator(hass: HomeAssistant, call: ServiceCall) -> MarsktekCoordinator:
    """Retrieve the coordinator for the device_id given in the service call."""
    device_id = call.data.get(ATTR_DEVICE_ID)
    coordinators: dict[str, MarsktekCoordinator] = hass.data.get(DOMAIN, {})
    if not coordinators:
        raise ServiceValidationError("No Marstek Venus E devices configured.")
    # If only one device, pick it automatically
    if len(coordinators) == 1:
        return next(iter(coordinators.values()))
    if device_id in coordinators:
        return coordinators[device_id]
    raise ServiceValidationError(
        f"Unknown device_id '{device_id}'. Available: {list(coordinators.keys())}"
    )


def _register_services(hass: HomeAssistant) -> None:
    """Register HA services (idempotent — skips if already registered)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_PASSIVE_MODE):
        return

    # ── set_passive_mode ─────────────────────────────────────────────────────
    async def handle_set_passive_mode(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        power   = call.data.get(ATTR_POWER, 0)
        cd_time = call.data.get(ATTR_CD_TIME, 0)
        ok = await coord.api.set_mode_passive(power=power, cd_time=cd_time)
        if ok:
            await coord.async_request_refresh()
        else:
            _LOGGER.warning("set_passive_mode: device returned set_result=false")

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PASSIVE_MODE,
        handle_set_passive_mode,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_DEVICE_ID):  cv.string,
                vol.Required(ATTR_POWER):      vol.All(int, vol.Range(min=-3000, max=3000)),
                vol.Optional(ATTR_CD_TIME, default=0): vol.All(int, vol.Range(min=0)),
            }
        ),
    )

    # ── set_manual_schedule ──────────────────────────────────────────────────
    async def handle_set_manual_schedule(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        ok = await coord.api.set_manual_schedule(
            time_num   = call.data[ATTR_TIME_NUM],
            start_time = call.data[ATTR_START_TIME],
            end_time   = call.data[ATTR_END_TIME],
            week_set   = call.data.get(ATTR_WEEK_SET, WEEK_ALL_DAYS),
            power      = call.data[ATTR_POWER],
            enable     = call.data.get(ATTR_ENABLE, True),
        )
        if ok:
            await coord.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MANUAL_SCHEDULE,
        handle_set_manual_schedule,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_DEVICE_ID):                        cv.string,
                vol.Required(ATTR_TIME_NUM):                         vol.All(int, vol.Range(min=0, max=9)),
                vol.Required(ATTR_START_TIME):                       cv.string,
                vol.Required(ATTR_END_TIME):                         cv.string,
                vol.Optional(ATTR_WEEK_SET, default=WEEK_ALL_DAYS):  vol.All(int, vol.Range(min=0, max=127)),
                vol.Required(ATTR_POWER):                            vol.All(int, vol.Range(min=-3000, max=3000)),
                vol.Optional(ATTR_ENABLE, default=True):             cv.boolean,
            }
        ),
    )

    # ── clear_schedules ──────────────────────────────────────────────────────
    async def handle_clear_schedules(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        await coord.api.clear_all_schedules()
        await coord.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_SCHEDULES,
        handle_clear_schedules,
        schema=vol.Schema({vol.Optional(ATTR_DEVICE_ID): cv.string}),
    )

    # ── force_refresh ────────────────────────────────────────────────────────
    async def handle_force_refresh(call: ServiceCall) -> None:
        coord = _get_coordinator(hass, call)
        await coord.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_REFRESH,
        handle_force_refresh,
        schema=vol.Schema({vol.Optional(ATTR_DEVICE_ID): cv.string}),
    )
