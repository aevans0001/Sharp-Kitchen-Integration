"""Data update coordinator for Sharp Kitchen."""

from __future__ import annotations

import logging
import math
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SharpKitchenClient, SharpKitchenError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SMART_COOK_PRESETS

_LOGGER = logging.getLogger(__name__)


class SharpKitchenCoordinator(DataUpdateCoordinator[dict[int, dict]]):
    """Poll device state and hold local, validated pending cook selections."""

    def __init__(self, hass: HomeAssistant, client: SharpKitchenClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.devices: dict[int, dict] = {}
        self.pending_cook_seconds: dict[int, int] = {}
        self.pending_power: dict[int, int] = {}
        self.pending_smart_cook_preset: dict[int, str] = {}
        # Values are always stored in the exact string form sent by the app.
        self.pending_smart_cook_value: dict[int, str] = {}

    def smart_cook_preset(self, device_id: int) -> str:
        return self.pending_smart_cook_preset.get(device_id, next(iter(SMART_COOK_PRESETS)))

    def smart_cook_definition(self, device_id: int) -> dict[str, object]:
        preset_id = self.smart_cook_preset(device_id)
        try:
            return SMART_COOK_PRESETS[preset_id]
        except KeyError as err:
            raise ValueError(f"Unknown Smart Cook preset: {preset_id}") from err

    def set_smart_cook_preset(self, device_id: int, preset_id: str) -> None:
        if preset_id not in SMART_COOK_PRESETS:
            raise ValueError(f"Unknown Smart Cook preset: {preset_id}")
        self.pending_smart_cook_preset[device_id] = preset_id
        # A previous numeric or option value must never leak into a new preset.
        self.pending_smart_cook_value.pop(device_id, None)
        self.async_update_listeners()

    @staticmethod
    def _format_numeric(value: float) -> str:
        value = round(float(value), 10)
        return str(int(value)) if value.is_integer() else format(value, ".10g")

    @staticmethod
    def _valid_numeric(value: float, preset: dict[str, object]) -> bool:
        minimum = float(preset["min_value"])
        maximum = float(preset["max_value"])
        step = float(preset["step"])
        if value < minimum - 1e-9 or value > maximum + 1e-9:
            return False
        steps = (value - minimum) / step
        return math.isclose(steps, round(steps), abs_tol=1e-9)

    def set_smart_cook_numeric(self, device_id: int, value: float) -> None:
        preset = self.smart_cook_definition(device_id)
        if preset["parameter_type"] != "numeric":
            raise ValueError("Selected Smart Cook preset does not use a numeric parameter")
        if not self._valid_numeric(float(value), preset):
            raise ValueError("Smart Cook value is outside the exact app range or increment")
        self.pending_smart_cook_value[device_id] = self._format_numeric(float(value))
        self.async_update_listeners()

    def set_smart_cook_option(self, device_id: int, label: str) -> None:
        preset = self.smart_cook_definition(device_id)
        if preset["parameter_type"] != "option":
            raise ValueError("Selected Smart Cook preset does not use an option parameter")
        for raw_value, option_label in dict(preset["options"]).items():
            if option_label == label:
                self.pending_smart_cook_value[device_id] = str(raw_value)
                self.async_update_listeners()
                return
        raise ValueError("Invalid Smart Cook option")

    def smart_cook_value(self, device_id: int) -> str:
        preset = self.smart_cook_definition(device_id)
        parameter_type = preset["parameter_type"]
        if parameter_type == "sensor":
            return "0"
        value = self.pending_smart_cook_value.get(device_id, str(preset["default_value"]))
        if parameter_type == "numeric":
            try:
                numeric = float(value)
            except (TypeError, ValueError) as err:
                raise ValueError("Smart Cook numeric value is invalid") from err
            if not self._valid_numeric(numeric, preset):
                raise ValueError("Smart Cook numeric value is outside the exact app rule")
            return self._format_numeric(numeric)
        if parameter_type == "option" and value in dict(preset["options"]):
            return value
        raise ValueError("Smart Cook option value is invalid")

    async def async_refresh_devices(self) -> dict[int, dict]:
        device_list = await self.client.async_get_devices()
        self.devices = {d["id"]: d for d in device_list}
        return self.devices

    async def _async_update_data(self) -> dict[int, dict]:
        if not self.devices:
            await self.async_refresh_devices()
        result: dict[int, dict] = {}
        try:
            for device_id, info in self.devices.items():
                state = await self.client.async_get_device_state(device_id)
                result[device_id] = {**info, **state}
        except SharpKitchenError as err:
            raise UpdateFailed(f"Error talking to Sharp Kitchen: {err}") from err
        return result