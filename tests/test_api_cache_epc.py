"""Behavioral tests for Sharp's late-2026 device/cache EPC requirement."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "sharp_kitchen"


def _load_api_module():
    """Load api.py without importing the HA integration package __init__."""
    package = types.ModuleType("sharp_kitchen")
    package.__path__ = [str(INTEGRATION)]
    sys.modules["sharp_kitchen"] = package

    const_spec = importlib.util.spec_from_file_location(
        "sharp_kitchen.const", INTEGRATION / "const.py"
    )
    const_module = importlib.util.module_from_spec(const_spec)
    sys.modules["sharp_kitchen.const"] = const_module
    assert const_spec.loader is not None
    const_spec.loader.exec_module(const_module)

    api_spec = importlib.util.spec_from_file_location(
        "sharp_kitchen.api", INTEGRATION / "api.py"
    )
    api_module = importlib.util.module_from_spec(api_spec)
    sys.modules["sharp_kitchen.api"] = api_module
    assert api_spec.loader is not None
    api_spec.loader.exec_module(api_module)
    return api_module


@pytest.mark.asyncio
async def test_legacy_cache_request_is_preserved(monkeypatch) -> None:
    api = _load_api_module()
    client = api.SharpKitchenClient(None, "refresh", "123456", "user")
    calls = []

    async def fake_request(method, path, *, params=None, json_body=None, retry=True):
        calls.append((method, path, params, retry))
        return {"state": {"cook": "off", "door": "close"}}

    monkeypatch.setattr(client, "_request", fake_request)

    state = await client.async_get_device_state(42)

    assert state == {"cook": "off", "door": "close"}
    assert calls == [
        ("GET", api.DEVICE_CACHE_PATH, {"device_id": 42}, True)
    ]
    assert client._cache_requires_epc is False


@pytest.mark.asyncio
async def test_missing_epc_switches_to_property_reads_and_preserves_settings(
    monkeypatch,
) -> None:
    api = _load_api_module()
    client = api.SharpKitchenClient(None, "refresh", "123456", "user")
    calls = []
    first_legacy = True

    states = {
        "B0": {"door": "close"},
        "B1": {"cook": "off"},
        "E3": {"temperature": "0"},
        "E6": {"rest_time": "0:00:00"},
        "E7": {"power": "0"},
    }

    async def fake_request(method, path, *, params=None, json_body=None, retry=True):
        nonlocal first_legacy
        calls.append((method, path, dict(params or {}), retry))

        if path == api.DEVICE_SETTING_PATH:
            return {"state": {"easy_wave": "on", "short_tone": "on"}}

        if path != api.DEVICE_CACHE_PATH:
            raise AssertionError(f"unexpected path: {path}")

        if "epc" not in (params or {}):
            if first_legacy:
                first_legacy = False
                raise api.SharpKitchenApiError(
                    1,
                    "bad request",
                    {"code": 400, "info": "epc is None.", "message": "Bad Request"},
                )
            raise AssertionError("legacy no-EPC cache request was repeated")

        epc = params["epc"]
        return {"state": states[epc]}

    monkeypatch.setattr(client, "_request", fake_request)

    state = await client.async_get_device_state(42)

    assert state == {
        "door": "close",
        "cook": "off",
        "temperature": "0",
        "rest_time": "0:00:00",
        "power": "0",
        "easy_wave": "on",
        "short_tone": "on",
    }
    assert client._cache_requires_epc is True
    assert client._cache_epc_encoding == "hex"
    assert [c[2].get("epc") for c in calls if c[1] == api.DEVICE_CACHE_PATH] == [
        None,
        "B0",
        "B1",
        "E3",
        "E6",
        "E7",
    ]

    calls.clear()
    await client.async_get_device_state(42)
    assert all(
        c[2].get("epc") is not None
        for c in calls
        if c[1] == api.DEVICE_CACHE_PATH
    )


@pytest.mark.asyncio
async def test_unrelated_bad_request_does_not_enable_epc_fallback(monkeypatch) -> None:
    api = _load_api_module()
    client = api.SharpKitchenClient(None, "refresh", "123456", "user")

    async def fake_request(method, path, *, params=None, json_body=None, retry=True):
        raise api.SharpKitchenApiError(
            1,
            "bad request",
            {"code": 400, "info": "some other request problem", "message": "Bad Request"},
        )

    monkeypatch.setattr(client, "_request", fake_request)

    with pytest.raises(api.SharpKitchenApiError):
        await client.async_get_device_state(42)

    assert client._cache_requires_epc is None
    assert client._cache_epc_encoding is None


@pytest.mark.asyncio
async def test_epc_encoding_probe_falls_back_to_decimal_and_caches_it(monkeypatch) -> None:
    api = _load_api_module()
    client = api.SharpKitchenClient(None, "refresh", "123456", "user")
    attempted = []

    async def fake_request(method, path, *, params=None, json_body=None, retry=True):
        if path == api.DEVICE_SETTING_PATH:
            return {"state": {}}

        if "epc" not in (params or {}):
            raise api.SharpKitchenApiError(
                1,
                "bad request",
                {"code": 400, "info": "epc is None.", "message": "Bad Request"},
            )

        attempted.append((params["epc"], retry))
        if params["epc"] == "B0":
            raise api.SharpKitchenApiError(
                1,
                "bad request",
                {"code": 400, "info": "invalid epc", "message": "Bad Request"},
            )
        return {"state": {"seen": params["epc"]}}

    monkeypatch.setattr(client, "_request", fake_request)

    state = await client.async_get_device_state(42)

    assert client._cache_epc_encoding == "decimal"
    assert attempted[:2] == [("B0", False), ("176", False)]
    assert [value for value, _ in attempted[2:]] == ["177", "227", "230", "231"]
    assert state["seen"] == "231"
