"""Number entities for Marstek Venus E — passive mode power & duration."""

from __future__ import annotations

import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODE_PASSIVE
from .coordinator import MarsktekCoordinator
from .sensor import _device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MarsktekCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            MarsktekPassivePower(coordinator, entry),
            MarsktekPassiveDuration(coordinator, entry),
        ]
    )


class MarsktekPassivePower(
    CoordinatorEntity[MarsktekCoordinator], NumberEntity, RestoreEntity
):
    """
    Set the passive mode target power.

    Positive  → discharge to grid (W)
    Negative  → charge from grid (W)

    Changing this number immediately sends ES.SetMode Passive if the battery
    is currently in Passive mode, otherwise it just stores the value.
    """

    _attr_has_entity_name = True
    _attr_name = "Passive Power Target"
    _attr_icon = "mdi:battery-arrow-up-outline"
    _attr_native_min_value = -3000
    _attr_native_max_value = 3000
    _attr_native_step = 100
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = NumberDeviceClass.POWER
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self, coordinator: MarsktekCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_passive_power"
        self._attr_device_info = _device_info(entry)
        self._entry = entry
        self._stored_power: float = 0.0

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state not in ("unknown", "unavailable", None):
            try:
                self._stored_power = float(last.state)
            except ValueError:
                pass

    @property
    def native_value(self) -> float:
        # Show the current ongrid_power when in passive mode
        if self.coordinator.data:
            mode = self.coordinator.data.get("mode")
            if mode == MODE_PASSIVE:
                return float(self.coordinator.data.get("ongrid_power", self._stored_power))
        return self._stored_power

    async def async_set_native_value(self, value: float) -> None:
        self._stored_power = value
        # Apply immediately if currently in passive mode
        if self.coordinator.data and self.coordinator.data.get("mode") == MODE_PASSIVE:
            ok = await self.coordinator.api.set_mode_passive(power=int(value), cd_time=0)
            if ok:
                await self.coordinator.async_request_refresh()
        self.async_write_ha_state()


class MarsktekPassiveDuration(
    CoordinatorEntity[MarsktekCoordinator], NumberEntity, RestoreEntity
):
    """Countdown duration for Passive mode (seconds, 0 = indefinite)."""

    _attr_has_entity_name = True
    _attr_name = "Passive Duration"
    _attr_icon = "mdi:timer-outline"
    _attr_native_min_value = 0
    _attr_native_max_value = 86400   # 24 h
    _attr_native_step = 60
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_mode = NumberMode.BOX

    def __init__(
        self, coordinator: MarsktekCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_passive_duration"
        self._attr_device_info = _device_info(entry)
        self._stored_duration: float = 0.0

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state not in ("unknown", "unavailable", None):
            try:
                self._stored_duration = float(last.state)
            except ValueError:
                pass

    @property
    def native_value(self) -> float:
        return self._stored_duration

    async def async_set_native_value(self, value: float) -> None:
        self._stored_duration = value
        self.async_write_ha_state()
