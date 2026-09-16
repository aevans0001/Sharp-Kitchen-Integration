"""Switches for the on/off-style Sharp Kitchen settings.

These map to {"command":"oven_setting","items":{"<key>":"on"/"off"}} calls.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SETTING_KEYS
from .coordinator import SharpKitchenCoordinator

# Human-friendly labels for the raw setting keys -- matching the names
# used in the real app's own Settings screen.
SETTING_LABELS = {
    "forget_take": "Reminder Sound",
    "short_tone": "Sound",
    "easy_wave": "Easy Wave",
}

# Clean entity_id object_ids for each -- see the comment at the top of
# button.py for why these are pinned explicitly.
SETTING_OBJECT_IDS = {
    "forget_take": "microwave_reminder_sound",
    "short_tone": "microwave_sound",
    "easy_wave": "microwave_easy_wave",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SharpKitchenCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        SharpKitchenSettingSwitch(coordinator, device_id, key)
        for device_id in coordinator.devices
        for key in SETTING_KEYS
    ]
    async_add_entities(entities)


class SharpKitchenSettingSwitch(CoordinatorEntity[SharpKitchenCoordinator], SwitchEntity):
    """A boolean on/off setting on a Sharp Kitchen device."""

    _attr_has_entity_name = True
    # Groups these under the device page's "Settings"/"Configuration"
    # section instead of mixing them in with the cook controls.
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: SharpKitchenCoordinator, device_id: int, key: str
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._key = key
        self._attr_name = SETTING_LABELS.get(key, key)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{key}"
        self._attr_suggested_object_id = SETTING_OBJECT_IDS.get(key, f"microwave_{key}")

    @property
    def _device(self) -> dict:
        return self.coordinator.data.get(self._device_id, {})

    @property
    def is_on(self) -> bool | None:
        value = self._device.get(self._key)
        if value is None:
            return None
        return str(value).lower() == "on"

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.async_set_setting(self._device_id, self._key, "on")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.async_set_setting(self._device_id, self._key, "off")
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        d = self._device
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=f"Microwave - Sharp {d.get('model_name') or 'SMD2489ES'}",
            manufacturer="Sharp",
            model=d.get("model_name"),
        )
