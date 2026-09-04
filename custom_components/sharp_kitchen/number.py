"""Number entities for setting up a manual cook before pressing Start.

These don't talk to Sharp's API by themselves -- they just record what
you want (on the coordinator, see coordinator.py) so that the "Start
Cook" button (in button.py) has something to send. This mirrors the real
app's own microwave control screen: set the time, set the power, then
press Start as a separate action.

Cook time is stored on the coordinator as a single total-seconds number
(pending_cook_seconds), but shown here as two entities -- minutes and
seconds -- since that's much easier to actually set with a slider than
one "seconds" number going up to 1800. Each one just reads/writes its
own piece of that same total.
"""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SMART_COOK_PRESETS
from .coordinator import SharpKitchenCoordinator

# Defaults used until the user sets these for the first time.
DEFAULT_COOK_SECONDS = 60
DEFAULT_POWER = 100
# The real app won't let you set a manual cook longer than 30 minutes.
MAX_COOK_SECONDS = 30 * 60


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SharpKitchenCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NumberEntity] = []
    for device_id in coordinator.devices:
        entities.append(SharpKitchenCookMinutesNumber(coordinator, device_id))
        entities.append(SharpKitchenCookSecondsNumber(coordinator, device_id))
        entities.append(SharpKitchenPowerNumber(coordinator, device_id))
        entities.append(SharpKitchenSmartCookWeightNumber(coordinator, device_id))
    async_add_entities(entities)


class _SharpKitchenPendingNumber(NumberEntity):
    """Shared plumbing for the "pending cook setting" numbers."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER
    # Not tied to live device state, so this doesn't need a coordinator
    # listener -- it only ever reflects what the user last set locally.
    _attr_should_poll = False

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        self._coordinator = coordinator
        self._device_id = device_id

    @property
    def device_info(self) -> DeviceInfo:
        d = self._coordinator.data.get(self._device_id, {})
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._device_id))},
            name=d.get("name", f"Sharp device {self._device_id}"),
            manufacturer="Sharp",
            model=d.get("model_name"),
        )

    @property
    def _total_seconds(self) -> int:
        return self._coordinator.pending_cook_seconds.get(self._device_id, DEFAULT_COOK_SECONDS)

    def _set_total_seconds(self, value: int) -> None:
        clamped = max(0, min(MAX_COOK_SECONDS, value))
        self._coordinator.pending_cook_seconds[self._device_id] = clamped


class SharpKitchenCookMinutesNumber(_SharpKitchenPendingNumber):
    _attr_name = "Cook Time (Minutes)"
    _attr_native_min_value = 0
    _attr_native_max_value = 30
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_cook_minutes"
        # Pinned explicitly so entity_id comes out as
        # "number.microwave_cook_time_minutes" instead of Home
        # Assistant's auto-guessed (and occasionally doubled-up) name.
        self._attr_suggested_object_id = "microwave_cook_time_minutes"

    @property
    def native_value(self) -> float:
        return self._total_seconds // 60

    async def async_set_native_value(self, value: float) -> None:
        seconds_part = self._total_seconds % 60
        self._set_total_seconds(int(value) * 60 + seconds_part)
        self.async_write_ha_state()


class SharpKitchenCookSecondsNumber(_SharpKitchenPendingNumber):
    _attr_name = "Cook Time (Seconds)"
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
        minutes_part = self._total_seconds // 60
        self._set_total_seconds(minutes_part * 60 + int(value))
        self.async_write_ha_state()


class SharpKitchenPowerNumber(_SharpKitchenPendingNumber):
    _attr_name = "Power Level"
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
        return self._coordinator.pending_power.get(self._device_id, DEFAULT_POWER)

    async def async_set_native_value(self, value: float) -> None:
        self._coordinator.pending_power[self._device_id] = int(value)
        self.async_write_ha_state()


class SharpKitchenSmartCookWeightNumber(_SharpKitchenPendingNumber):
    """Weight/quantity for whichever Smart Cook preset is currently
    selected on the "Smart Cook Preset" select entity (select.py). Its
    range and unit change to match that preset -- e.g. 0.5-2.0 lb for
    "Defrost Ground Meat" but 1-6 cup for "Hot Water"."""

    _attr_name = "Smart Cook Weight"
    _attr_native_step = 0.1
    _attr_icon = "mdi:scale"

    def __init__(self, coordinator: SharpKitchenCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_smart_cook_weight"
        self._attr_suggested_object_id = "microwave_smart_cook_weight"

    @property
    def _preset(self) -> dict:
        auto_number = self._coordinator.smart_cook_preset(self._device_id)
        return SMART_COOK_PRESETS[auto_number]

    @property
    def native_min_value(self) -> float:
        return self._preset["min_weight"]

    @property
    def native_max_value(self) -> float:
        return self._preset["max_weight"]

    @property
    def native_unit_of_measurement(self) -> str:
        return self._preset["unit"]

    @property
    def native_value(self) -> float:
        return self._coordinator.pending_smart_cook_weight.get(
            self._device_id, self._preset["default_weight"]
        )

    async def async_set_native_value(self, value: float) -> None:
        self._coordinator.pending_smart_cook_weight[self._device_id] = value
        self.async_write_ha_state()
