"""Sensor entities for Marstek Venus E."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_LABEL, CONF_MAC, DEFAULT_PORT, DOMAIN
from .coordinator import MarsktekCoordinator


@dataclass(frozen=True)
class MarsktekSensorDescription(SensorEntityDescription):
    """Extend SensorEntityDescription with a data key."""
    data_key: str = ""
    scale: float = 1.0


SENSOR_DESCRIPTIONS: tuple[MarsktekSensorDescription, ...] = (
    # ── Battery ──────────────────────────────────────────────────────────────
    MarsktekSensorDescription(
        key="battery_soc",
        data_key="soc",
        name="State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
    ),
    MarsktekSensorDescription(
        key="battery_capacity",
        data_key="bat_capacity",
        name="Battery Remaining Capacity",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging",
    ),
    MarsktekSensorDescription(
        key="battery_rated_capacity",
        data_key="rated_capacity",
        name="Battery Rated Capacity",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging-100",
        entity_registry_enabled_default=False,
    ),
    MarsktekSensorDescription(
        key="battery_temperature",
        data_key="bat_temp",
        name="Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
    ),
    # ── Power ─────────────────────────────────────────────────────────────────
    MarsktekSensorDescription(
        key="pv_power",
        data_key="pv_power",
        name="PV Solar Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
    ),
    MarsktekSensorDescription(
        key="grid_power",
        data_key="ongrid_power",
        name="Grid Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower",
    ),
    MarsktekSensorDescription(
        key="offgrid_power",
        data_key="offgrid_power",
        name="Off-Grid Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt",
    ),
    MarsktekSensorDescription(
        key="battery_power",
        data_key="bat_power",
        name="Battery Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging-outline",
    ),
    # ── CT / Energy meter phases ──────────────────────────────────────────────
    MarsktekSensorDescription(
        key="phase_a_power",
        data_key="phase_a_power",
        name="Phase A Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:alpha-a-circle",
        entity_registry_enabled_default=False,
    ),
    MarsktekSensorDescription(
        key="phase_b_power",
        data_key="phase_b_power",
        name="Phase B Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:alpha-b-circle",
        entity_registry_enabled_default=False,
    ),
    MarsktekSensorDescription(
        key="phase_c_power",
        data_key="phase_c_power",
        name="Phase C Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:alpha-c-circle",
        entity_registry_enabled_default=False,
    ),
    MarsktekSensorDescription(
        key="total_ct_power",
        data_key="total_ct_power",
        name="Total CT Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:meter-electric",
    ),
    # ── Energy totals (kWh) ───────────────────────────────────────────────────
    MarsktekSensorDescription(
        key="total_pv_energy",
        data_key="total_pv_energy",
        name="Total PV Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:solar-power-variant",
    ),
    MarsktekSensorDescription(
        key="total_grid_export",
        data_key="total_grid_export",
        name="Total Grid Export",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-export",
    ),
    MarsktekSensorDescription(
        key="total_grid_import",
        data_key="total_grid_import",
        name="Total Grid Import",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-import",
    ),
    MarsktekSensorDescription(
        key="total_load_energy",
        data_key="total_load_energy",
        name="Total Load Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:home-lightning-bolt-outline",
    ),
    # ── WiFi ─────────────────────────────────────────────────────────────────
    MarsktekSensorDescription(
        key="wifi_signal",
        data_key="wifi_rssi",
        name="WiFi Signal",
        native_unit_of_measurement="dBm",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wifi",
        entity_registry_enabled_default=False,
    ),
    # ── Operating mode (string) ───────────────────────────────────────────────
    MarsktekSensorDescription(
        key="operating_mode",
        data_key="mode",
        name="Operating Mode",
        icon="mdi:battery-sync",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: MarsktekCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MarsktekSensor(coordinator, entry, desc) for desc in SENSOR_DESCRIPTIONS
    )


class MarsktekSensor(CoordinatorEntity[MarsktekCoordinator], SensorEntity):
    """A single Marstek sensor entity."""

    entity_description: MarsktekSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MarsktekCoordinator,
        entry: ConfigEntry,
        description: MarsktekSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        val = self.coordinator.data.get(self.entity_description.data_key)
        if val is None:
            return None
        # Apply scale factor if defined (not default 1.0)
        scale = self.entity_description.scale
        if scale != 1.0 and isinstance(val, (int, float)):
            return round(val * scale, 3)
        return val


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get(CONF_DEVICE_LABEL, "Marstek Venus E"),
        manufacturer="Marstek",
        model="Venus E 3.0",
        sw_version=None,
        configuration_url=f"http://{entry.data.get('host', '')}",
    )
