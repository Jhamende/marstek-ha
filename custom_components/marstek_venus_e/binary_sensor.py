"""Binary sensor entities for Marstek Venus E."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MarsktekCoordinator
from .sensor import _device_info


@dataclass(frozen=True)
class MarsktekBinarySensorDescription(BinarySensorEntityDescription):
    data_key: str = ""
    # value that means "on" — if callable, it receives the raw value
    on_value: Any = True


BINARY_SENSOR_DESCRIPTIONS: tuple[MarsktekBinarySensorDescription, ...] = (
    MarsktekBinarySensorDescription(
        key="charging",
        data_key="charg_flag",
        name="Charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        icon="mdi:battery-charging",
        on_value=True,
    ),
    MarsktekBinarySensorDescription(
        key="discharging",
        data_key="dischrg_flag",
        name="Discharging",
        icon="mdi:battery-arrow-down",
        on_value=True,
    ),
    MarsktekBinarySensorDescription(
        key="ct_connected",
        data_key="ct_state",
        name="CT Meter Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:current-ac",
        on_value=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MarsktekCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MarsktekBinarySensor(coordinator, entry, desc)
        for desc in BINARY_SENSOR_DESCRIPTIONS
    )


class MarsktekBinarySensor(
    CoordinatorEntity[MarsktekCoordinator], BinarySensorEntity
):
    entity_description: MarsktekBinarySensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MarsktekCoordinator,
        entry: ConfigEntry,
        description: MarsktekBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        val = self.coordinator.data.get(self.entity_description.data_key)
        if val is None:
            return None
        return val == self.entity_description.on_value
