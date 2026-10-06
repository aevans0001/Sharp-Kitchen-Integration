# Sharp Kitchen Integration

Unofficial Home Assistant custom integration for Sharp Kitchen-connected appliances, built and tested with the Sharp SMD2489ES Microwave Drawer.

## Supported and verified behavior

- Sharp Kitchen account sign-in through the same hosted login flow used by the official app.
- Automatic token refresh and cloud communication.
- Manual microwave controls: cook time, power level, start, pause, stop, and open drawer.
- Smart Cook support for the full 29-program SMD2489ES catalog.
  - Numeric programs expose the applicable quantity/weight control.
  - Option programs expose the applicable option selector.
  - Sensor programs use the appliance's sensor-cook behavior.
- Device settings: Easy Wave, Sound, and Reminder Sound.
- Sensors for status, drawer/door state, remaining time, power, and temperature.

The currently verified appliance is the Sharp SMD2489ES. Other Sharp Kitchen-connected appliances may use related cloud APIs, but their controls are not claimed as supported until they are specifically verified.

## Installation

### HACS

HACS packaging is being prepared. Until the first release is published, install this repository as a custom HACS integration only for testing.

1. In HACS, add this repository as a custom repository with category **Integration**.
2. Install **Sharp Kitchen**.
3. Restart Home Assistant.
4. Go to **Settings > Devices & services > Add integration** and search for **Sharp Kitchen**.
5. Sign in with the same account used by the Sharp Kitchen app.

### Manual

1. Copy `custom_components/sharp_kitchen` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings > Devices & services > Add integration** and search for **Sharp Kitchen**.

## Smart Cook

The integration contains the 29-program SMD2489ES Smart Cook catalog. The Home Assistant entities adapt to the selected program:

- **Weight/quantity** for numeric programs such as Beverage Reheat.
- **Option** for programs such as Soften Ice Cream.
- No secondary value for sensor programs such as Fish / Seafood.

A low-level `sharp_kitchen.start_smart_cook` action remains available for backward compatibility, but normal use should go through the validated entities.

## Notes

- This integration communicates with Sharp's cloud service and therefore requires internet access.
- The project is reverse engineered from observed behavior of the official Sharp Kitchen app because no public Sharp Kitchen API is known.
- Appliance writes should be treated like physical appliance controls: verify the selected program/settings before starting a cook cycle.

## Development and validation

Release preparation includes HACS validation and Home Assistant hassfest validation. The repository intentionally contains only the Home Assistant integration; Appliance Control Center/dashboard presentation logic is maintained separately.

## Disclaimer

This project is unofficial and is not affiliated with or endorsed by Sharp Corporation.
