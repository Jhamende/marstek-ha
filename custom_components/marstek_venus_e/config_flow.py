"""Config flow for Marstek Venus E."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .api import MarsktekAPI, MarsktekAPIError, MarsktekTimeoutError
from .const import (
    CONF_DEVICE_LABEL,
    CONF_MAC,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_DISCOVERY = "discovery"
STEP_MANUAL    = "manual"
STEP_CONFIRM   = "confirm"


class MarsktekConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow: network discovery → confirm, or manual IP entry."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_devices: list[dict[str, Any]] = []
        self._selected_device: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Entry point — offer discovery or manual."""
        return await self.async_step_discovery_start()

    # ── Step 1 : run discovery ────────────────────────────────────────────────

    async def async_step_discovery_start(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Broadcast on the LAN and offer found devices."""
        errors: dict[str, str] = {}

        if user_input is None:
            # First time: scan the network
            _LOGGER.debug("Starting Marstek discovery broadcast…")
            try:
                self._discovered_devices = await MarsktekAPI.discover_devices(
                    port=DEFAULT_PORT
                )
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.warning("Discovery failed: %s", exc)
                self._discovered_devices = []

        # Build choice list: discovered devices + "manual" option
        options: dict[str, str] = {}
        for dev in self._discovered_devices:
            label = f"{dev.get('device', 'Marstek')}  —  {dev['ip']}  (fw v{dev.get('ver', '?')})"
            options[dev["ip"]] = label
        options["__manual__"] = "Entrer l'adresse IP manuellement"

        if user_input is not None:
            choice = user_input.get("device_choice")
            if choice == "__manual__":
                return await self.async_step_manual()
            # Find chosen device
            for dev in self._discovered_devices:
                if dev["ip"] == choice:
                    self._selected_device = dev
                    return await self.async_step_confirm()
            errors["base"] = "unknown_device"

        return self.async_show_form(
            step_id="discovery_start",
            data_schema=vol.Schema(
                {vol.Required("device_choice"): vol.In(options)}
            ),
            description_placeholders={
                "count": str(len(self._discovered_devices))
            },
            errors=errors,
        )

    # ── Step 2a : manual IP ───────────────────────────────────────────────────

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for IP + port manually."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            # Try to connect and fetch device info
            api = MarsktekAPI(host, port)
            try:
                await api.connect()
                bat = await api.get_bat_status()
                await api.close()
            except (MarsktekTimeoutError, MarsktekAPIError):
                errors["base"] = "cannot_connect"
                await api.close()
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"
                await api.close()
            else:
                self._selected_device = {
                    "ip": host,
                    "device": "VenusE 3.0",
                    "ver": "?",
                    "ble_mac": "",
                }
                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                        int, vol.Range(min=1024, max=65535)
                    ),
                }
            ),
            errors=errors,
        )

    # ── Step 2b : confirm discovered device ───────────────────────────────────

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm and let user set a friendly name + scan interval."""
        dev = self._selected_device
        errors: dict[str, str] = {}

        if user_input is not None:
            label    = user_input[CONF_DEVICE_LABEL]
            interval = user_input[CONF_SCAN_INTERVAL]
            host     = dev["ip"]
            port     = user_input.get(CONF_PORT, DEFAULT_PORT)
            mac      = dev.get("ble_mac", "")

            # Prevent duplicate entries for same IP
            await self.async_set_unique_id(f"marstek_{host.replace('.', '_')}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=label or f"Marstek {host}",
                data={
                    CONF_HOST:         host,
                    CONF_PORT:         port,
                    CONF_MAC:          mac,
                    CONF_DEVICE_LABEL: label,
                    CONF_SCAN_INTERVAL: interval,
                },
            )

        default_label = f"Marstek {dev.get('device', 'Venus')} {dev['ip']}"
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_LABEL, default=default_label): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                        int, vol.Range(min=1024, max=65535)
                    ),
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): vol.All(int, vol.Range(min=30, max=3600)),
                }
            ),
            description_placeholders={
                "device": dev.get("device", "Marstek"),
                "ip":     dev["ip"],
                "fw":     str(dev.get("ver", "?")),
            },
        )

    # ── Options flow (reconfiguration) ────────────────────────────────────────

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return MarsktekOptionsFlow(config_entry)


class MarsktekOptionsFlow(config_entries.OptionsFlow):
    """Allow changing scan interval and device label after initial setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        current = self._config_entry.data
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get(CONF_DEVICE_LABEL, current.get(CONF_DEVICE_LABEL, "")),
                data=user_input,
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_LABEL,
                        default=current.get(CONF_DEVICE_LABEL, ""),
                    ): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(int, vol.Range(min=30, max=3600)),
                }
            ),
            errors=errors,
        )
