"""Config flow for Sharp Kitchen."""

from __future__ import annotations

import logging
import random

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SharpKitchenAuthError, SharpKitchenClient, async_hosted_ui_login, get_cognito_username
from .const import CONF_COGNITO_USERNAME, CONF_PHONE_ID, CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class SharpKitchenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sharp Kitchen."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            try:
                auth_result = await async_hosted_ui_login(
                    session, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                )
            except SharpKitchenAuthError as err:
                _LOGGER.error("Sharp Kitchen login failed: %s", err)
                errors["base"] = "invalid_auth"
            else:
                refresh_token = auth_result["RefreshToken"]

                try:
                    # The Cognito user's real internal username (often a
                    # random UUID, not the email) -- needed to correctly
                    # compute SECRET_HASH on every future token refresh.
                    username = get_cognito_username(auth_result["AccessToken"])
                except SharpKitchenAuthError as err:
                    _LOGGER.error("Sharp Kitchen login succeeded but token was unreadable: %s", err)
                    errors["base"] = "invalid_auth"
                else:
                    # A stable, distinct ID for this Home Assistant instance
                    # as a "paired phone" on the account. Generated once and
                    # kept forever in the config entry so we don't
                    # re-register a new phone on every restart.
                    phone_id = str(random.randint(100000, 999999))

                    # Verify everything works end-to-end and pull the device
                    # list so we can show something useful in the entry title.
                    client = SharpKitchenClient(
                        session, refresh_token, phone_id, username
                    )
                    try:
                        devices = await client.async_get_devices()
                    except Exception as err:  # noqa: BLE001
                        _LOGGER.exception("Sharp Kitchen setup verification failed")
                        errors["base"] = "cannot_connect"
                    else:
                        await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                        self._abort_if_unique_id_configured()

                        device_count = len(devices)
                        title = (
                            f"Sharp Kitchen ({device_count} device"
                            f"{'s' if device_count != 1 else ''})"
                        )
                        return self.async_create_entry(
                            title=title,
                            data={
                                CONF_REFRESH_TOKEN: client.refresh_token,
                                CONF_PHONE_ID: phone_id,
                                CONF_COGNITO_USERNAME: username,
                            },
                        )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
