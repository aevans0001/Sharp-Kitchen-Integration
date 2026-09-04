# Sharp Kitchen Integration

A Home Assistant custom integration for Sharp Kitchen-connected appliances
(built and tested against a Sharp SMD2489ES microwave), talking directly
to Sharp's real cloud API.

## Features

- Real Cognito Hosted-UI OAuth2 login (with automatic token refresh) and
  mutual TLS client-certificate authentication to Sharp's device API.
- Manual cook control: cook time (minutes/seconds), power level,
  Start/Pause/Stop, Open Drawer.
- Smart Cook presets (built-in automatic cook programs), with a
  preset selector, weight/quantity slider, and Start button.
- Device settings exposed as switches: Easy Wave, Sound, Reminder Sound.
- Sensors: status, door state, time remaining, power, temperature.

## Installation

1. Copy the `custom_components/sharp_kitchen` folder into your Home
   Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to Settings > Devices & Services > Add Integration, search for
   "Sharp Kitchen", and log in with your Sharp Kitchen account
   credentials.

## Status

Core cook/control functionality is fully working. Only 3 of Sharp's
~30 built-in Smart Cook presets are currently mapped (Defrost Ground
Meat, Beverage Reheat, Hot Water) — more will be added as they're
captured from the real app.

## Disclaimer

This is an unofficial, community-reverse-engineered integration. It is
not affiliated with or endorsed by Sharp Corporation.
