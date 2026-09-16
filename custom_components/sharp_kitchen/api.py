"""Thin async client for the Sharp Kitchen (na-kitchen) backend and the
AWS Cognito user pool it authenticates against.

Everything in here is reverse-engineered from the Sharp Kitchen app's own
traffic. It is NOT based on any public Sharp API documentation -- none is
known to exist. In particular:

  * The initial email+password login uses Cognito's hosted-UI OAuth2
    "authorization code" flow (see async_hosted_ui_login below and the
    long comment in const.py). This IS verified against the real app's
    actual login traffic (captured via Chrome remote-debugging on the
    app's login WebView, since that traffic is invisible to an OkHttp
    hook -- WebViews use their own separate network stack). An earlier
    version of this integration instead called Cognito's direct
    USER_PASSWORD_AUTH API, which was never actually what the app does;
    it produced a token missing "version": 2 and part of the real scope,
    and Sharp's API rejected it every time with "fail to get user
    subject". REFRESH_TOKEN_AUTH (used for everything after the first
    login, via async_cognito_refresh) is unaffected by this -- it's a
    separate, simpler flow and was already verified against captured
    native (OkHttp) traffic.

  * Every call to Sharp's device API (device.na-api.aiot.sharp.co.jp,
    including account/initialize itself) additionally requires mutual
    TLS -- the client must present a certificate, not just a valid
    access token. Without it, requests come back rejected too. See
    _client_ssl_context() below and the comment on CLIENT_CERT_B64 in
    const.py.

  * The `f2` field returned by the device is an opaque hex bitmask. It is
    passed through as a raw attribute but not decoded.

  * Sharp's Cognito app client requires a "SECRET_HASH" on every direct
    Cognito auth call (currently just token refresh) -- this is an HMAC
    computed from a client secret. That secret was recovered from the
    app's own bundled JavaScript originally, and has since been
    independently confirmed: it's the same secret encoded in the
    "Authorization: Basic ..." header the real app sends on its
    hosted-UI token exchange. See the comment on COGNITO_CLIENT_SECRET in
    const.py.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import ssl
import asyncio
import tempfile
import time
import urllib.parse
from typing import Any

import aiohttp
from cryptography import x509
from cryptography.hazmat.primitives import serialization

from .const import (
    API_BASE,
    CLIENT_CERT_B64,
    CLIENT_KEY_B64,
    COGNITO_CLIENT_ID,
    COGNITO_CLIENT_SECRET,
    COGNITO_ENDPOINT,
    DEVICE_CACHE_PATH,
    DEVICE_CONTROL_PATH,
    DEVICE_SETTING_PATH,
    INITIALIZE_PATH,
    OAUTH_HOST,
    OAUTH_REDIRECT_URI,
    OAUTH_SCOPE,
    OAUTH_TOKEN_URL,
    OAUTH_USER_AGENT,
    PAIRING_PATH,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


def _secret_hash(username: str) -> str:
    """Cognito's required SECRET_HASH: base64(HMAC-SHA256(client secret,
    username + client_id)). `username` must be the *exact* string used as
    USERNAME in the request this hash is attached to."""
    digest = hmac.new(
        COGNITO_CLIENT_SECRET.encode("utf-8"),
        (username + COGNITO_CLIENT_ID).encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def get_cognito_username(access_token: str) -> str:
    """Pull the Cognito user's real internal username out of an access
    token JWT. This is often a random UUID, not the email -- and it's
    what's needed (not the email) to correctly compute SECRET_HASH on
    later token refreshes."""
    parts = access_token.split(".")
    if len(parts) != 3:
        raise SharpKitchenAuthError("Access token doesn't look like a JWT (expected 3 dot-separated parts).")
    payload_b64 = parts[1]
    padding = "=" * (-len(payload_b64) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
    except Exception as err:  # noqa: BLE001
        raise SharpKitchenAuthError(f"Couldn't decode access token payload: {err}") from err
    username = payload.get("username")
    if not username:
        raise SharpKitchenAuthError("Access token JWT has no 'username' claim.")
    return username


_client_ssl_context: ssl.SSLContext | None = None


def _build_client_ssl_context() -> ssl.SSLContext:
    """Build (once, then cache) the SSLContext used for mutual TLS to
    Sharp's device API. See the module docstring and the CLIENT_CERT_B64
    comment in const.py for why this is required at all.

    Python's ssl module can only load a client certificate/key from
    actual files, not from bytes in memory, so this decodes them to a
    couple of temporary files just long enough to load them into the
    SSLContext, then deletes the temp files immediately -- the loaded
    SSLContext itself doesn't need them anymore afterward.

    Uses ssl.create_default_context() (not a bare ssl.SSLContext(...))
    specifically so the system's normal trusted root certificates get
    loaded too -- a plain SSLContext() only loads what you explicitly
    hand it, which without this fix meant it had our own client cert but
    nothing to verify *Sharp's* server certificate against, and every
    connection failed with "unable to get local issuer certificate".
    """
    global _client_ssl_context
    if _client_ssl_context is not None:
        return _client_ssl_context

    cert_der = base64.b64decode(CLIENT_CERT_B64)
    key_der = base64.b64decode(CLIENT_KEY_B64)
    cert_pem = x509.load_der_x509_certificate(cert_der).public_bytes(serialization.Encoding.PEM)
    key = serialization.load_der_private_key(key_der, password=None)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    cert_path = key_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as cert_f:
            cert_f.write(cert_pem)
            cert_path = cert_f.name
        with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as key_f:
            key_f.write(key_pem)
            key_path = key_f.name

        ctx = ssl.create_default_context()
        ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
    finally:
        if cert_path:
            os.unlink(cert_path)
        if key_path:
            os.unlink(key_path)

    _client_ssl_context = ctx
    return ctx


async def _get_client_ssl_context() -> ssl.SSLContext:
    """Return the cached mTLS context without blocking HA's event loop."""
    global _client_ssl_context
    if _client_ssl_context is None:
        _client_ssl_context = await asyncio.to_thread(_build_client_ssl_context)
    return _client_ssl_context


class SharpKitchenError(Exception):
    """Base error for anything going wrong talking to Sharp's backend."""


class SharpKitchenAuthError(SharpKitchenError):
    """Raised when Cognito login/refresh fails."""


class SharpKitchenApiError(SharpKitchenError):
    """Raised when the na-kitchen API itself returns a non-zero result_code."""

    def __init__(self, result_code: Any, result_msg: str, data: Any = None):
        self.result_code = result_code
        self.result_msg = result_msg
        self.data = data
        super().__init__(f"Sharp API error {result_code}: {result_msg!r} (data={data!r})")


async def _cognito_request(
    session: aiohttp.ClientSession, target: str, payload: dict
) -> dict:
    """POST a request to the Cognito Identity Provider service."""
    headers = {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": f"AWSCognitoIdentityProviderService.{target}",
    }
    async with session.post(COGNITO_ENDPOINT, json=payload, headers=headers) as resp:
        body = await resp.json(content_type=None)
        if resp.status != 200:
            err_type = body.get("__type", "UnknownError")
            err_msg = body.get("message") or body.get("Message") or str(body)
            raise SharpKitchenAuthError(f"Cognito {target} failed: {err_type}: {err_msg}")
        return body


async def async_hosted_ui_login(
    session: aiohttp.ClientSession, email: str, password: str
) -> dict:
    """Log in the way the real app actually does: through Cognito's
    hosted web login page (OAuth2 "authorization code" flow), not a
    direct Cognito API call. See the module docstring and const.py for
    why -- this replaces an earlier, wrong implementation.

    Returns a dict shaped like Cognito's own AuthenticationResult
    (AccessToken, RefreshToken, IdToken, ExpiresIn) so callers don't need
    to care which login method was used.

    Deliberately does NOT rely on the session's cookie jar (Home
    Assistant's shared aiohttp session may not keep one at all, to avoid
    leaking cookies between unrelated integrations) -- the CSRF cookie
    from step 1 is read directly off that response and re-sent by hand
    as an explicit header in step 2.
    """
    login_url = (
        f"{OAUTH_HOST}/login"
        f"?response_type=code&client_id={COGNITO_CLIENT_ID}"
        f"&identity_provider=COGNITO"
        f"&redirect_uri={urllib.parse.quote(OAUTH_REDIRECT_URI, safe='')}"
        f"&scope={urllib.parse.quote(OAUTH_SCOPE)}"
    )
    common_headers = {
        "User-Agent": OAUTH_USER_AGENT,
        "X-Requested-With": "com.sharpusa.iotdrawer",
    }

    # Step 1: load the login page just to get a fresh CSRF token.
    async with session.get(login_url, headers=common_headers) as resp:
        await resp.read()
        csrf_cookie = resp.cookies.get("XSRF-TOKEN")

    if not csrf_cookie:
        raise SharpKitchenAuthError(
            "Sharp's login page didn't return an XSRF-TOKEN cookie; can't "
            "log in. (Sharp may have changed how this page works.)"
        )
    csrf_token = csrf_cookie.value

    # Step 2: submit credentials. The real form sends "_csrf" twice
    # (two identical hidden fields) -- reproduced here for fidelity,
    # though a single copy would likely work too.
    form_data = aiohttp.FormData()
    form_data.add_field("_csrf", csrf_token)
    form_data.add_field("_csrf", csrf_token)
    form_data.add_field("username", email)
    form_data.add_field("password", password)

    async with session.post(
        login_url,
        data=form_data,
        headers={
            **common_headers,
            "Origin": OAUTH_HOST,
            "Referer": login_url,
            "Cookie": f"XSRF-TOKEN={csrf_token}",
        },
        allow_redirects=True,
    ) as resp:
        final_url = str(resp.url)
        await resp.read()

    code = urllib.parse.parse_qs(urllib.parse.urlparse(final_url).query).get("code", [None])[0]
    if not code:
        raise SharpKitchenAuthError(
            "Login didn't reach a page with an authorization code -- this "
            "usually means the email or password is wrong. (If they're "
            "definitely correct, Sharp's login page may now require an "
            "extra device-fingerprint field this integration doesn't send.)"
        )

    # Step 3: exchange the one-time code for real tokens.
    basic_auth = base64.b64encode(f"{COGNITO_CLIENT_ID}:{COGNITO_CLIENT_SECRET}".encode()).decode()
    async with session.post(
        OAUTH_TOKEN_URL,
        headers={
            **common_headers,
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://sharphomeuser.sharpusa.com:8287",
            "Referer": "https://sharphomeuser.sharpusa.com:8287/",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": OAUTH_REDIRECT_URI,
        },
    ) as resp:
        body = await resp.json(content_type=None)
        if resp.status != 200:
            raise SharpKitchenAuthError(f"Token exchange failed: HTTP {resp.status}: {body!r}")

    if "access_token" not in body:
        raise SharpKitchenAuthError(f"Token exchange returned no access_token: {body!r}")

    return {
        "AccessToken": body["access_token"],
        "RefreshToken": body.get("refresh_token"),
        "IdToken": body.get("id_token"),
        "ExpiresIn": body.get("expires_in", 3600),
    }


async def async_cognito_refresh(
    session: aiohttp.ClientSession, refresh_token: str, username: str
) -> dict:
    """Exchange a refresh token for a fresh access token.

    `username` must be the Cognito user's real internal username (from
    get_cognito_username), not the email -- it's only used locally to
    compute SECRET_HASH, it isn't sent to Cognito as its own parameter.
    """
    body = await _cognito_request(
        session,
        "InitiateAuth",
        {
            "AuthFlow": "REFRESH_TOKEN_AUTH",
            "ClientId": COGNITO_CLIENT_ID,
            "AuthParameters": {
                "REFRESH_TOKEN": refresh_token,
                "SECRET_HASH": _secret_hash(username),
            },
        },
    )
    result = body.get("AuthenticationResult")
    if not result:
        raise SharpKitchenAuthError(f"Cognito refresh returned no AuthenticationResult: {body!r}")
    return result


class SharpKitchenClient:
    """Client for the na-kitchen device API.

    Handles keeping a valid `cloud_key` (Sharp's own session credential,
    obtained via account/initialize using a Cognito access token) and
    re-fetching it automatically when a call fails auth.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        refresh_token: str,
        phone_id: str,
        username: str,
        phone_name: str = "Home Assistant",
    ) -> None:
        self._session = session
        self._refresh_token = refresh_token
        self._phone_id = phone_id
        self._username = username
        self._phone_name = phone_name
        self._access_token: str | None = None
        self._cloud_key: str | None = None
        self._access_token_expiry: float = 0.0

    @property
    def refresh_token(self) -> str:
        return self._refresh_token

    async def _ensure_access_token(self) -> None:
        """Make sure we have a non-expired Cognito access token."""
        if self._access_token and time.time() < self._access_token_expiry - 60:
            return
        result = await async_cognito_refresh(self._session, self._refresh_token, self._username)
        self._access_token = result["AccessToken"]
        self._access_token_expiry = time.time() + result.get("ExpiresIn", 3600)
        # Cognito's REFRESH_TOKEN_AUTH normally doesn't rotate the refresh
        # token, but handle it just in case a future app-client config does.
        if result.get("RefreshToken"):
            self._refresh_token = result["RefreshToken"]
        # A new access token means our cloud_key is stale too.
        self._cloud_key = None

    async def _ensure_cloud_key(self) -> None:
        await self._ensure_access_token()
        if self._cloud_key:
            return
        payload = {
            "init_ver": "ver2",
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "phone_name": self._phone_name,
            "fcm_token": "",
            "phone_id": str(self._phone_id),
        }
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": USER_AGENT,
            # The real app sends these on every call, including this one --
            # blank on a first-ever call, or the still-valid old key on a
            # later re-initialize.
            "X-cloud-key": self._cloud_key or "",
            "X-api-key": "",
        }
        async with self._session.post(
            API_BASE + INITIALIZE_PATH,
            json=payload,
            headers=headers,
            ssl=await _get_client_ssl_context(),
        ) as resp:
            try:
                body = await resp.json(content_type=None)
            except Exception as err:  # noqa: BLE001
                text = await resp.text()
                raise SharpKitchenError(
                    f"account/initialize returned non-JSON (HTTP {resp.status}): {text[:300]!r}"
                ) from err
        data = self._unwrap(body)
        self._cloud_key = data["cloud_key"]

    @staticmethod
    def _unwrap(body: dict) -> Any:
        """Pull `data` out of the standard {data, result_code, result_msg}
        envelope, raising SharpKitchenApiError on a non-zero result_code."""
        result_code = body.get("result_code")
        if result_code not in (0, "0", None):
            raise SharpKitchenApiError(result_code, body.get("result_msg", ""), body.get("data"))
        return body.get("data")

    async def _request(self, method: str, path: str, *, params=None, json_body=None, retry=True) -> Any:
        await self._ensure_cloud_key()
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": USER_AGENT,
            "X-cloud-key": self._cloud_key,
            "X-api-key": "",
        }
        async with self._session.request(
            method,
            API_BASE + path,
            params=params,
            json=json_body,
            headers=headers,
            ssl=await _get_client_ssl_context(),
        ) as resp:
            try:
                body = await resp.json(content_type=None)
            except Exception as err:  # pragma: no cover - defensive
                text = await resp.text()
                raise SharpKitchenError(
                    f"Non-JSON response from {path} (HTTP {resp.status}): {text[:300]!r}"
                ) from err

        try:
            return self._unwrap(body)
        except SharpKitchenApiError:
            # A stale cloud_key most often shows up as a generic API error.
            # Force a fresh one and retry exactly once.
            if retry:
                self._cloud_key = None
                return await self._request(
                    method, path, params=params, json_body=json_body, retry=False
                )
            raise

    # --- Public API ---

    async def async_get_devices(self) -> list[dict]:
        """Return the list of devices paired to this account."""
        data = await self._request("GET", PAIRING_PATH)
        return data.get("device_info", [])

    async def async_get_device_state(self, device_id: int) -> dict:
        """Return full/live state for one device (cook status, door, etc.)."""
        data = await self._request(
            "GET", DEVICE_CACHE_PATH, params={"device_id": device_id}
        )
        return data.get("state", {})

    async def async_get_device_settings(self, device_id: int) -> dict:
        """Return just the basic settings block for one device."""
        data = await self._request(
            "GET", DEVICE_SETTING_PATH, params={"device_id": device_id}
        )
        return data.get("state", {})

    async def async_set_setting(self, device_id: int, key: str, value: str) -> None:
        await self._request(
            "POST",
            DEVICE_CONTROL_PATH,
            json_body={
                "command": "oven_setting",
                "items": {key: value},
                "device_id": device_id,
            },
        )

    async def async_start_cook(
        self,
        device_id: int,
        *,
        mode: str = "microwave",
        cook_time: str = "0:01:00",
        power: int | None = None,
        temperature: int | None = None,
        with_preheat: bool = False,
    ) -> None:
        """Start a manual cook.

        `cook_time` must be "H:MM:SS". Only `mode="microwave"` with a
        `power` level was actually exercised in testing; `temperature` and
        other `mode` values (e.g. convection/grill/oven modes this model or
        other Sharp appliances may support) are wired through but
        unverified.
        """
        await self._request(
            "POST",
            DEVICE_CONTROL_PATH,
            json_body={
                "command": "cook_manual",
                "manual_convection_menu": mode,
                "manual_time": cook_time,
                "manual_power": power,
                "manual_temperature": temperature,
                "with_preheat": "TRUE" if with_preheat else "FALSE",
                "device_id": device_id,
            },
        )

    async def async_stop_cook(self, device_id: int) -> None:
        await self._request(
            "POST",
            DEVICE_CONTROL_PATH,
            json_body={"command": "cook_stop", "device_id": device_id},
        )

    async def async_pause_cook(self, device_id: int) -> None:
        """Pause the current cook. Captured directly off the real app's
        traffic (via Frida), same as everything else in this file."""
        await self._request(
            "POST",
            DEVICE_CONTROL_PATH,
            json_body={"command": "cook_pause", "device_id": device_id},
        )

    async def async_open_door(self, device_id: int) -> None:
        """Open the drawer/door. Captured directly off the real app's
        "Open Drawer" button."""
        await self._request(
            "POST",
            DEVICE_CONTROL_PATH,
            json_body={"command": "door_open", "device_id": device_id},
        )

    async def async_start_smart_cook(
        self, device_id: int, auto_number: str, auto_weight: str
    ) -> None:
        """Start one of Sharp's built-in "Smart Cook" presets (the
        Beverage/Defrost/Fish/Frozen Entree/... grid in the real app).

        `auto_number` identifies which preset (e.g. "D7001") and
        `auto_weight` is the weight/quantity for it (e.g. "1.2") -- both
        exactly as captured from the real app's traffic. All 29 SMD2489ES
        Microwave Drawer presets are cataloged in SMART_COOK_PRESETS
        (const.py); use the Smart Cook entities for normal use.
        """
        await self._request(
            "POST",
            DEVICE_CONTROL_PATH,
            json_body={
                "command": "cook_smart",
                "auto_number": auto_number,
                "auto_weight": str(auto_weight),
                "device_id": device_id,
            },
        )
