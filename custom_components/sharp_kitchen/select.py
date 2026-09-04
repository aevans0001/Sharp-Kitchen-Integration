""""Smart Cook Preset" select entity -- picks which of Sharp's built-in
presets (see SMART_COOK_PRESETS in const.py) the "Start Smart Cook"
button (in button.py) will run, and what range/unit the "Smart Cook
Weight" number entity (in number.py) should use.
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SMART_COOK_PRESETS
from .coordinator import SharpKitchenCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SharpKitchenCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SharpKitchenSmartCookPresetSelect(coordinator, device_id)
        for device_id in coordinator.devices
    )


class SharpKitchenSmartCookPresetSelect(SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Smart Cook Preset"
    _attr_icon = "mdi:chef-hat"
    _attr_should_poll = False

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        self._coordinator = coordinator
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}_smart_cook_preset"
        self._attr_suggested_object_id = "microwave_smart_cook_preset"
        self._attr_options = [preset["name"] for preset in SMART_COOK_PRESETS.values()]

    @property
    def current_option(self) -> str | None:
        auto_number = self._coordinator.smart_cook_preset(self._device_id)
        return SMART_COOK_PRESETS[auto_number]["name"]

    async def async_select_option(self, option: str) -> None:
        for auto_number, preset in SMART_COOK_PRESETS.items():
            if preset["name"] == option:
                self._coordinator.pending_smart_cook_preset[self._device_id] = auto_number
                # Reset the weight/quantity to this preset's own default
                # any time the preset changes, same as the real app
                # re-showing its own default when you pick a new one.
                self._coordinator.pending_smart_cook_weight[self._device_id] = preset[
                    "default_weight"
                ]
                break
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        d = self._coordinator.data.get(self._device_id, {})
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=d.get("name", f"Sharp device {self._device_id}"),
            manufacturer="Sharp",
            model=d.get("model_name"),
        )
