"""Data update coordinator for Sharp Kitchen -- polls every paired device's
state on a timer and hands it to all entities at once."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SharpKitchenClient, SharpKitchenError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SMART_COOK_PRESETS

_LOGGER = logging.getLogger(__name__)


class SharpKitchenCoordinator(DataUpdateCoordinator[dict[int, dict]]):
    """Polls na-kitchen for every device's state.

    self.data ends up as {device_id: {**device_info_from_pairing, **live_state}}
    """

    def __init__(self, hass: HomeAssistant, client: SharpKitchenClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.devices: dict[int, dict] = {}  # static info: name, model, mac...
        # Desired manual-cook settings, held here (not on any one entity) so
        # a "Cook Time" number entity, a "Power Level" number entity, and a
        # "Start Cook" button can all share them: the two number entities
        # just update these dicts, and pressing Start reads whatever is in
        # them at that moment. Defaults are a sane fallback if the user
        # presses Start without touching the sliders first.
        self.pending_cook_seconds: dict[int, int] = {}
        self.pending_power: dict[int, int] = {}
        # Same idea for Smart Cook: which preset (by auto_number) and what
        # weight/quantity, shared between a select entity, a number
        # entity, and a "Start Smart Cook" button.
        self.pending_smart_cook_preset: dict[int, str] = {}
        self.pending_smart_cook_weight: dict[int, float] = {}

    def smart_cook_preset(self, device_id: int) -> str:
        """The currently selected preset's auto_number for this device,
        defaulting to the first known preset."""
        return self.pending_smart_cook_preset.get(device_id, next(iter(SMART_COOK_PRESETS)))

    async def async_refresh_devices(self) -> dict[int, dict]:
        """Fetch the (mostly static) list of paired devices. Call once at
        setup, and again if a new device might have been paired."""
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
