"""'Start Cook' and 'Stop Cook' buttons per device.

Starting a cook also needs a time and a power level -- those live on the
"Cook Time" and "Power Level" number entities (see number.py) rather than
on this button, the same way the real app's own screen has you set a
slider before pressing a separate Start button. This pair is also still
available as the `sharp_kitchen.start_cook` service (see services.yaml)
for anyone who wants to call it from an automation/script with explicit
values instead.
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SharpKitchenCoordinator
from .number import DEFAULT_COOK_SECONDS, DEFAULT_POWER


# Every entity below sets _attr_suggested_object_id explicitly instead of
# letting Home Assistant guess one from the device name + entity name.
# That auto-guessing is what produced the doubled-up
# "kitchen_kitchen_microwave_..." entity IDs on some entities earlier --
# pinning this ourselves guarantees a clean "microwave_..." entity_id
# for any entity created from now on (a fresh install, or ever adding a
# second Sharp device -- Home Assistant will just append "_2" to that
# second device's entities rather than reusing the same object_id).


def _seconds_to_hms(total_seconds: int) -> str:
    """423 -> "0:07:03", matching the "H:MM:SS" the API expects."""
    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SharpKitchenCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = []
    for device_id in coordinator.devices:
        entities.append(SharpKitchenStartButton(coordinator, device_id))
        entities.append(SharpKitchenPauseButton(coordinator, device_id))
        entities.append(SharpKitchenStopButton(coordinator, device_id))
        entities.append(SharpKitchenOpenDoorButton(coordinator, device_id))
        entities.append(SharpKitchenStartSmartCookButton(coordinator, device_id))
    async_add_entities(entities)


class SharpKitchenStartButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Manual Cook - ⏵︎ Start"
    _attr_icon = "mdi:microwave"

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        self._coordinator = coordinator
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}_start_cook"
        self._attr_suggested_object_id = "microwave_start_cook"

    async def async_press(self) -> None:
        cook_seconds = self._coordinator.pending_cook_seconds.get(
            self._device_id, DEFAULT_COOK_SECONDS
        )
        power = self._coordinator.pending_power.get(self._device_id, DEFAULT_POWER)
        await self._coordinator.client.async_start_cook(
            self._device_id,
            mode="microwave",
            cook_time=_seconds_to_hms(cook_seconds),
            power=power,
        )
        await self._coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        d = self._coordinator.data.get(self._device_id, {})
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=f"Microwave - Sharp {d.get('model_name') or 'SMD2489ES'}",
            manufacturer="Sharp",
            model=d.get("model_name"),
        )


class SharpKitchenStopButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Manual Cook - ■ Stop"

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        self._coordinator = coordinator
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}_stop_cook"
        self._attr_suggested_object_id = "microwave_stop_cook"

    async def async_press(self) -> None:
        await self._coordinator.client.async_stop_cook(self._device_id)
        await self._coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        d = self._coordinator.data.get(self._device_id, {})
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=f"Microwave - Sharp {d.get('model_name') or 'SMD2489ES'}",
            manufacturer="Sharp",
            model=d.get("model_name"),
        )


class SharpKitchenPauseButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Manual Cook - ⏸︎ Pause"
    _attr_icon = "mdi:pause"

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        self._coordinator = coordinator
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}_pause_cook"
        self._attr_suggested_object_id = "microwave_pause_cook"

    async def async_press(self) -> None:
        await self._coordinator.client.async_pause_cook(self._device_id)
        await self._coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        d = self._coordinator.data.get(self._device_id, {})
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=f"Microwave - Sharp {d.get('model_name') or 'SMD2489ES'}",
            manufacturer="Sharp",
            model=d.get("model_name"),
        )


class SharpKitchenOpenDoorButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Drawer - Open"
    _attr_icon = "mdi:door-open"

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        self._coordinator = coordinator
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}_open_door"
        self._attr_suggested_object_id = "microwave_open_drawer"

    async def async_press(self) -> None:
        await self._coordinator.client.async_open_door(self._device_id)
        await self._coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        d = self._coordinator.data.get(self._device_id, {})
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=f"Microwave - Sharp {d.get('model_name') or 'SMD2489ES'}",
            manufacturer="Sharp",
            model=d.get("model_name"),
        )


class SharpKitchenStartSmartCookButton(ButtonEntity):
    """Runs whatever preset + weight are currently set on the "Smart Cook
    Preset" select entity and "Smart Cook Weight" number entity."""

    _attr_has_entity_name = True
    _attr_name = "Smart Cook - ⏵︎ Start"
    _attr_icon = "mdi:chef-hat"

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        self._coordinator = coordinator
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}_start_smart_cook"
        self._attr_suggested_object_id = "microwave_start_smart_cook"

    async def async_press(self) -> None:
        auto_number = self._coordinator.smart_cook_preset(self._device_id)
        try:
            value = self._coordinator.smart_cook_value(self._device_id)
        except ValueError as err:
            raise HomeAssistantError(f"Invalid Smart Cook selection: {err}") from err
        await self._coordinator.client.async_start_smart_cook(
            self._device_id, auto_number, value
        )
        await self._coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        d = self._coordinator.data.get(self._device_id, {})
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=f"Microwave - Sharp {d.get('model_name') or 'SMD2489ES'}",
            manufacturer="Sharp",
            model=d.get("model_name"),
        )
