# Repository Metadata — Pending GitHub Settings Update

Proposed GitHub repository description:

> Home Assistant integration for Sharp Kitchen-connected appliances, including the SMD2489ES Microwave Drawer.

Proposed repository topics:

- home-assistant
- homeassistant
- hacs
- custom-integration
- sharp
- sharp-kitchen
- microwave
- smd2489es
- smart-home

These values are release-preparation metadata only. They do not authorize a
release or HACS submission.


## Exact GitHub CLI command

The connected GitHub toolset used during release preparation cannot mutate
repository About/Topics settings. If GitHub CLI is already authenticated, the
remaining metadata can be applied with:

```powershell
Clear-Host
gh repo edit aevans0001/Sharp-Kitchen-Integration --description "Home Assistant integration for Sharp Kitchen-connected appliances, including the SMD2489ES Microwave Drawer." --add-topic home-assistant --add-topic homeassistant --add-topic hacs --add-topic custom-integration --add-topic sharp --add-topic sharp-kitchen --add-topic microwave --add-topic smd2489es --add-topic smart-home

```

Applying repository description/topics does not merge the release PR, tag a
release, change authentication, or publish to HACS.
