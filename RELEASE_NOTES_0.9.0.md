# Sharp Kitchen 0.9.0 — Draft Release Notes

> **Not for publication yet.** The formal release is blocked until the Sharp
> application credential and shared mTLS private-key distribution problem has
> an acceptable public-release architecture.

## Highlights

- Home Assistant support for the Sharp SMD2489ES Microwave Drawer.
- Manual cook controls for cook time, power, start, pause, and stop.
- Drawer open control.
- Full 29-program SMD2489ES Smart Cook catalog.
- Adaptive Smart Cook controls:
  - numeric quantity/weight controls where required;
  - option selectors where required;
  - sensor-cook programs without an unnecessary secondary value.
- Easy Wave, Sound, and Reminder Sound settings.
- Sensors for appliance status, drawer/door state, remaining time, power,
  and temperature.
- UI-based Home Assistant configuration.
- HACS repository metadata and validation workflows.
- Original brand-neutral microwave-drawer icon added for HACS/Home Assistant presentation.
- Integration-wide actions registered once at Home Assistant integration
  setup rather than once per config entry.
- English translations include both low-level cook actions.

## Compatibility

The Sharp SMD2489ES is the currently verified appliance. Support for other
Sharp Kitchen-connected appliances is not claimed until those appliances are
specifically verified.

## Security / release blocker

The working implementation currently depends on application authentication
material recovered from the official Sharp Kitchen application, including
mTLS client key material. Those working values remain unchanged on the
preserved implementation while a distribution architecture is investigated.

No tag, GitHub release, or HACS default-store submission should be created
until that blocker is resolved and release validation is repeated.

## Release preparation status

- MIT License selected.
- Offline release-readiness tests pass.
- Home Assistant hassfest passes.
- HACS validation now passes all repository/integration checks after the GitHub description and topics were applied.
- Authentication research now documents Sharp's newer SHARP HOME ecosystem for later appliance revisions, but no public provisioning/API path has yet been found that resolves the existing Sharp Kitchen mTLS blocker.
- Draft PR #1 remains unmerged.
- No `0.9.0` tag or GitHub release exists.

## Disclaimer

Sharp Kitchen Integration is an unofficial community project and is not
affiliated with or endorsed by Sharp Corporation.
