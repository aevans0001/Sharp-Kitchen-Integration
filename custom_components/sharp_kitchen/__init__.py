"""The Sharp Kitchen integration.

Talks to the same backend the Sharp Kitchen Android app uses to control
Sharp IoT kitchen appliances (tested against a Sharp SMD2489ES microwave
drawer; the API itself is generic across whatever devices are paired to
the account, so other Sharp IoT appliances should work too, though their
exact `cook_manual` parameters -- mode names, whether they use
`manual_power` or `manual_temperature` -- are unverified beyond the
microwave this was built against).
"""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SharpKitchenClient
from .const import CONF_COGNITO_USERNAME, CONF_PHONE_ID, CONF_REFRESH_TOKEN, DOMAIN
from .coordinator import SharpKitchenCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "switch", "button", "number", "select"]

SERVICE_START_COOK = "start_cook"
SERVICE_START_SMART_COOK = "start_smart_cook"

START_COOK_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.Coerce(int),
        vol.Optional("mode", default="microwave"): cv.string,
        vol.Optional("cook_time", default="0:01:00"): cv.string,
        vol.Optional("power"): vol.Coerce(int),
        vol.Optional("temperature"): vol.Coerce(int),
        vol.Optional("with_preheat", default=False): cv.boolean,
    }
)

START_SMART_COOK_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.Coerce(int),
        vol.Required("auto_number"): cv.string,
        vol.Required("auto_weight"): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    client = SharpKitchenClient(
        session,
        refresh_token=entry.data[CONF_REFRESH_TOKEN],
        phone_id=entry.data[CONF_PHONE_ID],
        username=entry.data[CONF_COGNITO_USERNAME],
    )

    coordinator = SharpKitchenCoordinator(hass, client)
    await coordinator.async_refresh_devices()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _handle_start_cook(call: ServiceCall) -> None:
        await client.async_start_cook(
            call.data["device_id"],
            mode=call.data["mode"],
            cook_time=call.data["cook_time"],
            power=call.data.get("power"),
            temperature=call.data.get("temperature"),
            with_preheat=call.data["with_preheat"],
        )
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_START_COOK, _handle_start_cook, schema=START_COOK_SCHEMA
    )

    async def _handle_start_smart_cook(call: ServiceCall) -> None:
        await client.async_start_smart_cook(
            call.data["device_id"],
            call.data["auto_number"],
            call.data["auto_weight"],
        )
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_SMART_COOK,
        _handle_start_smart_cook,
        schema=START_SMART_COOK_SCHEMA,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
