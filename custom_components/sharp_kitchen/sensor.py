"""Sensors for Sharp Kitchen devices."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SharpKitchenCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SharpKitchenCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SharpKitchenSensor] = []
    for device_id in coordinator.devices:
        entities.append(
            SharpKitchenSensor(coordinator, device_id, "cook", "Status", "microwave_status")
        )
        entities.append(
            SharpKitchenSensor(coordinator, device_id, "door", "Door", "microwave_door")
        )
        entities.append(
            SharpKitchenSensor(
                coordinator,
                device_id,
                "rest_time",
                "Time Remaining",
                "microwave_time_remaining",
            )
        )
        entities.append(
            SharpKitchenSensor(coordinator, device_id, "power", "Power", "microwave_power")
        )
        entities.append(
            SharpKitchenSensor(
                coordinator, device_id, "temperature", "Temperature", "microwave_temperature"
            )
        )
    async_add_entities(entities)


class SharpKitchenSensor(CoordinatorEntity[SharpKitchenCoordinator], SensorEntity):
    """A single state field on a Sharp Kitchen device, exposed as a sensor."""

    _attr_has_entity_name = True
    # Puts these in the device page's "Diagnostic" section, further down
    # the page than Controls/Settings, rather than at the top.
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: SharpKitchenCoordinator,
        device_id: int,
        field: str,
        name: str,
        object_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._field = field
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{field}"
        # Pinned explicitly -- see the comment at the top of button.py for
        # why (avoids Home Assistant's occasionally-doubled auto-guess).
        self._attr_suggested_object_id = object_id

    @property
    def _device(self) -> dict:
        return self.coordinator.data.get(self._device_id, {})

    @property
    def native_value(self):
        return self._device.get(self._field)

    @property
    def device_info(self) -> DeviceInfo:
        d = self._device
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=d.get("name", f"Sharp device {self._device_id}"),
            manufacturer="Sharp",
            model=d.get("model_name"),
            connections=(
                {("mac", d["mac_address"])} if d.get("mac_address") else set()
            ),
        )
