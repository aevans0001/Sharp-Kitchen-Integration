"""Number entities for local manual-cook and exact Smart Cook setup."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SharpKitchenCoordinator

DEFAULT_COOK_SECONDS = 60
DEFAULT_POWER = 100
MAX_COOK_SECONDS = 30 * 60


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SharpKitchenCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NumberEntity] = []
    for device_id in coordinator.devices:
        entities.extend((
            SharpKitchenCookMinutesNumber(coordinator, device_id),
            SharpKitchenCookSecondsNumber(coordinator, device_id),
            SharpKitchenPowerNumber(coordinator, device_id),
            SharpKitchenSmartCookWeightNumber(coordinator, device_id),
        ))
    async_add_entities(entities)


class _SharpKitchenPendingNumber(CoordinatorEntity[SharpKitchenCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER
    _attr_should_poll = False

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def device_info(self) -> DeviceInfo:
        device = self.coordinator.data.get(self._device_id, {})
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=f"Microwave - Sharp {device.get('model_name') or 'SMD2489ES'}",
            manufacturer="Sharp",
            model=device.get("model_name"),
        )

    @property
    def _total_seconds(self) -> int:
        return self.coordinator.pending_cook_seconds.get(self._device_id, DEFAULT_COOK_SECONDS)

    def _set_total_seconds(self, value: int) -> None:
        self.coordinator.pending_cook_seconds[self._device_id] = max(0, min(MAX_COOK_SECONDS, value))


class SharpKitchenCookMinutesNumber(_SharpKitchenPendingNumber):
    _attr_name = "Manual Cook - Time Minutes"
    _attr_native_min_value = 0
    _attr_native_max_value = 30
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_cook_minutes"
        self._attr_suggested_object_id = "microwave_cook_time_minutes"

    @property
    def native_value(self) -> float:
        return self._total_seconds // 60

    async def async_set_native_value(self, value: float) -> None:
        self._set_total_seconds(int(value) * 60 + self._total_seconds % 60)
        self.coordinator.async_update_listeners()


class SharpKitchenCookSecondsNumber(_SharpKitchenPendingNumber):
    _attr_name = "Manual Cook - Time Seconds"
    _attr_native_min_value = 0
    _attr_native_max_value = 59
    _attr_native_step = 5
    _attr_native_unit_of_measurement = "s"
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_cook_seconds"
        self._attr_suggested_object_id = "microwave_cook_time_seconds"

    @property
    def native_value(self) -> float:
        return self._total_seconds % 60

    async def async_set_native_value(self, value: float) -> None:
        self._set_total_seconds(self._total_seconds // 60 * 60 + int(value))
        self.coordinator.async_update_listeners()


class SharpKitchenPowerNumber(_SharpKitchenPendingNumber):
    _attr_name = "Manual Cook - Power Level"
    _attr_native_min_value = 10
    _attr_native_max_value = 100
    _attr_native_step = 10
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:radiator"

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_power_level"
        self._attr_suggested_object_id = "microwave_power_level"

    @property
    def native_value(self) -> float:
        return self.coordinator.pending_power.get(self._device_id, DEFAULT_POWER)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.pending_power[self._device_id] = int(value)
        self.coordinator.async_update_listeners()


class SharpKitchenSmartCookWeightNumber(_SharpKitchenPendingNumber):
    """The exact app numeric selector for the currently selected preset."""

    _attr_name = "Smart Cook - Weight"
    _attr_icon = "mdi:scale"

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_smart_cook_weight"
        self._attr_suggested_object_id = "microwave_smart_cook_weight"

    @property
    def _preset(self) -> dict[str, object]:
        return self.coordinator.smart_cook_definition(self._device_id)

    @property
    def available(self) -> bool:
        return super().available and self._preset["parameter_type"] == "numeric"

    @property
    def native_min_value(self) -> float:
        return float(self._preset.get("min_value", 0))

    @property
    def native_max_value(self) -> float:
        return float(self._preset.get("max_value", 0))

    @property
    def native_step(self) -> float:
        return float(self._preset.get("step", 1))

    @property
    def native_unit_of_measurement(self) -> str | None:
        unit = self._preset.get("unit")
        return str(unit) if unit else None

    @property
    def native_value(self) -> float | None:
        if self._preset["parameter_type"] != "numeric":
            return None
        return float(self.coordinator.smart_cook_value(self._device_id))

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_smart_cook_numeric(self._device_id, value)