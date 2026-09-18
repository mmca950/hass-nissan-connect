"""Sensors for Nissan vehicles: fuel range, odometer, and tire pressures."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.const import UnitOfLength, UnitOfPressure
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,  # pyright: ignore[reportPrivateImportUsage]
    SensorDeviceClass,  # pyright: ignore[reportPrivateImportUsage]
)

from .api.schema import VehicleStatus

from . import VehicleRuntimeData
from .entity import NissanCoordinatorEntity, async_vehicle_entry_setup


@dataclass(frozen=True, kw_only=True)
class NissanSensorDescription(SensorEntityDescription):
    value_fn: Callable[[VehicleStatus], Any]


def _tire(status: VehicleStatus, key: str) -> Any:
    """Tire pressure, guarded: this platform omits `pressure` on some vehicles."""
    pressure = status.pressure
    if pressure is None:
        return None
    return pressure[key].value


def _fuel_range(status: VehicleStatus) -> Any:
    cockpit = status.cockpit
    if cockpit is None or cockpit.fuelAutonomy is None:
        return None
    return cockpit.fuelAutonomy.value


def _odometer(status: VehicleStatus) -> Any:
    cockpit = status.cockpit
    if cockpit is None or cockpit.totalMileage is None:
        return None
    return cockpit.totalMileage.value


SENSOR_TYPES: tuple[NissanSensorDescription, ...] = (
    NissanSensorDescription(
        key="fuel_range",
        name="Range",
        icon="mdi:gas-station",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_fuel_range,
    ),
    NissanSensorDescription(
        key="odometer",
        name="Odometer",
        icon="mdi:counter",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_odometer,
    ),
    *(
        NissanSensorDescription(
            key=key,
            name=name,
            icon="mdi:tire",
            device_class=SensorDeviceClass.PRESSURE,
            native_unit_of_measurement=UnitOfPressure.PSI,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,
            value_fn=(lambda s, k=key: _tire(s, k)),
        )
        for key, name in (
            ("flPressure", "Front Left Tire Pressure"),
            ("frPressure", "Front Right Tire Pressure"),
            ("rlPressure", "Rear Left Tire Pressure"),
            ("rrPressure", "Rear Right Tire Pressure"),
        )
    ),
)


@async_vehicle_entry_setup
def async_setup_entry(runtime_data: VehicleRuntimeData):
    """Set up the Nissan sensors from config entry."""
    return [
        NissanSensor(runtime_data.status_coordinator, sensor)
        for sensor in SENSOR_TYPES
    ]


class NissanSensor(NissanCoordinatorEntity[VehicleStatus], SensorEntity):
    """A Nissan status-derived sensor."""

    entity_description: NissanSensorDescription

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.data)
