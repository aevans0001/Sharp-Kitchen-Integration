"""Smart Cook preset and exact option-selection entities."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SMART_COOK_PRESETS
from .coordinator import SharpKitchenCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SharpKitchenCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = []
    for device_id in coordinator.devices:
        entities.append(SharpKitchenSmartCookPresetSelect(coordinator, device_id))
        entities.append(SharpKitchenSmartCookOptionSelect(coordinator, device_id))
    async_add_entities(entities)


class _SharpKitchenSmartCookSelect(CoordinatorEntity[SharpKitchenCoordinator], SelectEntity):
    _attr_has_entity_name = True
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


class SharpKitchenSmartCookPresetSelect(_SharpKitchenSmartCookSelect):
    _attr_name = "Smart Cook - Preset"
    _attr_icon = "mdi:chef-hat"

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_smart_cook_preset"
        self._attr_suggested_object_id = "microwave_smart_cook_preset"
        self._attr_options = [preset["name"] for preset in SMART_COOK_PRESETS.values()]

    @property
    def current_option(self) -> str | None:
        return str(self.coordinator.smart_cook_definition(self._device_id)["name"])

    async def async_select_option(self, option: str) -> None:
        for preset_id, preset in SMART_COOK_PRESETS.items():
            if preset["name"] == option:
                self.coordinator.set_smart_cook_preset(self._device_id, preset_id)
                return
        raise ValueError("Unknown Smart Cook preset option")


class SharpKitchenSmartCookOptionSelect(_SharpKitchenSmartCookSelect):
    _attr_name = "Smart Cook - Option"
    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_smart_cook_option"
        self._attr_suggested_object_id = "microwave_smart_cook_option"

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.smart_cook_definition(self._device_id)["parameter_type"] == "option"

    @property
    def options(self) -> list[str]:
        preset = self.coordinator.smart_cook_definition(self._device_id)
        if preset["parameter_type"] != "option":
            return []
        return [str(label) for label in dict(preset["options"]).values()]

    @property
    def current_option(self) -> str | None:
        preset = self.coordinator.smart_cook_definition(self._device_id)
        if preset["parameter_type"] != "option":
            return None
        raw_value = self.coordinator.smart_cook_value(self._device_id)
        return str(dict(preset["options"])[raw_value])

    async def async_select_option(self, option: str) -> None:
        self.coordinator.set_smart_cook_option(self._device_id, option)