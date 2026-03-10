"""Select entity — operating mode selector for Marstek Venus E."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MODE_AI,
    MODE_AUTO,
    MODE_MANUAL,
    MODE_PASSIVE,
    OPERATING_MODES,
)
from .coordinator import MarsktekCoordinator
from .sensor import _device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MarsktekCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MarsktekModeSelect(coordinator, entry)])


class MarsktekModeSelect(CoordinatorEntity[MarsktekCoordinator], SelectEntity):
    """
    Dropdown to switch between Auto / AI / Manual / Passive modes.

    Note: switching to Passive via this entity uses power=0, cd_time=0 (indefinite).
    Use the service marstek_venus_e.set_passive_mode to specify power and duration.
    """

    _attr_has_entity_name = True
    _attr_name = "Operating Mode"
    _attr_icon = "mdi:battery-sync"
    _attr_options = OPERATING_MODES

    def __init__(
        self, coordinator: MarsktekCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_mode_select"
        self._attr_device_info = _device_info(entry)

    @property
    def current_option(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("mode")

    async def async_select_option(self, option: str) -> None:
        """Called when the user picks a new mode from the dropdown."""
        api = self.coordinator.api
        ok = False

        if option == MODE_AUTO:
            ok = await api.set_mode_auto()
        elif option == MODE_AI:
            ok = await api.set_mode_ai()
        elif option == MODE_MANUAL:
            # Switch to manual with a disabled placeholder in slot 9
            ok = await api.set_mode_manual(
                time_num=9,
                start_time="00:00",
                end_time="00:01",
                week_set=127,
                power=0,
                enable=0,
            )
        elif option == MODE_PASSIVE:
            # Power=0 / indefinite — user should then call set_passive_mode service
            ok = await api.set_mode_passive(power=0, cd_time=0)
        else:
            _LOGGER.warning("Unknown mode requested: %s", option)
            return

        if ok:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.warning("Mode change to %s returned set_result=false", option)
