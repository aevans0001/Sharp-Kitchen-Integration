"""Release-readiness tests that do not contact Sharp or a live appliance."""

from __future__ import annotations

import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "sharp_kitchen"


def _constants() -> dict:
    return runpy.run_path(INTEGRATION / "const.py")


def test_manifest_identity_and_proposed_version() -> None:
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["domain"] == "sharp_kitchen"
    assert manifest["name"] == "Sharp Kitchen"
    assert manifest["version"] == "0.9.0"
    assert manifest["config_flow"] is True
    assert manifest["iot_class"] == "cloud_polling"


def test_hacs_metadata_is_valid_json() -> None:
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    assert hacs["name"] == "Sharp Kitchen"


def test_smart_cook_catalog_has_all_29_programs() -> None:
    presets = _constants()["SMART_COOK_PRESETS"]
    assert len(presets) == 29
    assert len({preset["name"] for preset in presets.values()}) == 29
    assert {preset["parameter_type"] for preset in presets.values()} == {
        "numeric",
        "option",
        "sensor",
    }


def test_smart_cook_catalog_parameter_rules() -> None:
    presets = _constants()["SMART_COOK_PRESETS"]

    for preset_id, preset in presets.items():
        parameter_type = preset["parameter_type"]
        assert preset_id
        assert preset["name"]
        assert preset["category"]

        if parameter_type == "numeric":
            minimum = float(preset["min_value"])
            maximum = float(preset["max_value"])
            default = float(preset["default_value"])
            step = float(preset["step"])
            assert minimum <= default <= maximum
            assert step > 0
            assert preset.get("unit")
        elif parameter_type == "option":
            options = preset["options"]
            assert options
            assert str(preset["default_value"]) in options
            assert all(str(key) and str(label) for key, label in options.items())
        else:
            assert parameter_type == "sensor"
            assert str(preset["default_value"]) == "0"


def test_english_translation_covers_both_actions() -> None:
    translation = json.loads(
        (INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8")
    )
    services = translation["services"]
    assert "start_cook" in services
    assert "start_smart_cook" in services


def test_custom_integration_does_not_ship_core_strings_json() -> None:
    assert not (INTEGRATION / "strings.json").exists()


def test_mit_license_is_present() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("MIT License")
    assert "Permission is hereby granted, free of charge" in license_text
    assert "Copyright (c) 2026 aevans0001" in license_text


def test_release_blocker_is_documented() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Formal HACS release is currently **blocked**" in readme
    assert "There is no published `0.9.0` release yet" in readme


def test_brand_icon_is_256_square_png() -> None:
    icon = INTEGRATION / "brand" / "icon.png"
    data = icon.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert data[12:16] == b"IHDR"
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    assert (width, height) == (256, 256)
