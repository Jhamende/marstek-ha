"""Button entities for Marstek Venus E — quick mode shortcuts."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Awaitable

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MarsktekCoordinator
from .sensor import _device_info

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarsktekButtonDescription(ButtonEntityDescription):
    action: str = ""   # name of async method on MarsktekAPI


BUTTON_DESCRIPTIONS: tuple[MarsktekButtonDescription, ...] = (
    MarsktekButtonDescription(
        key="mode_auto",
        name="Set Mode: Auto",
        icon="mdi:autorenew",
        action="set_mode_auto",
    ),
    MarsktekButtonDescription(
        key="mode_ai",
        name="Set Mode: AI",
        icon="mdi:robot",
        action="set_mode_ai",
    ),
    MarsktekButtonDescription(
        key="force_refresh",
        name="Refresh Data",
        icon="mdi:refresh",
        action="",   # handled specially
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MarsktekCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MarsktekButton(coordinator, entry, desc) for desc in BUTTON_DESCRIPTIONS
    )


class MarsktekButton(CoordinatorEntity[MarsktekCoordinator], ButtonEntity):
    """A button that triggers a one-shot action on the battery."""

    entity_description: MarsktekButtonDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MarsktekCoordinator,
        entry: ConfigEntry,
        description: MarsktekButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _device_info(entry)

    async def async_press(self) -> None:
        desc = self.entity_description

        if desc.key == "force_refresh":
            await self.coordinator.async_request_refresh()
            return

        if desc.action:
            method = getattr(self.coordinator.api, desc.action, None)
            if method is None:
                _LOGGER.error("Unknown API action: %s", desc.action)
                return
            ok = await method()
            if ok:
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.warning("Button %s: device returned set_result=false", desc.key)
