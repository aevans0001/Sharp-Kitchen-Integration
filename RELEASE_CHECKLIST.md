# Sharp Kitchen 0.9.0 Release Checklist

This checklist is intentionally conservative. Completing preparation items does
not authorize a release.

## Hard blockers

- [ ] Replace the current public-distribution model for the Sharp application
      credential and shared mTLS private key.
- [ ] Confirm the replacement authentication design without breaking the
      currently working integration.
- [ ] Repeat privacy/confidential-data review after the authentication change.

## Repository / HACS

- [x] Public GitHub repository
- [x] One Home Assistant integration under `custom_components/sharp_kitchen`
- [x] `hacs.json`
- [x] README
- [x] MIT LICENSE
- [x] Issue tracker URL in manifest
- [x] Code owner in manifest
- [x] Versioned custom integration manifest
- [x] HACS validation workflow
- [x] hassfest workflow
- [x] Release-readiness tests
- [ ] Apply GitHub repository description
- [ ] Apply GitHub repository topics
- [ ] Add approved original brand icon
- [ ] HACS validation passes with no failed checks

## Validation

- [x] Offline release-readiness tests pass
- [x] hassfest passes after manifest/schema cleanup
- [ ] HACS validation passes
- [ ] Re-run all checks at final release commit
- [ ] Review final diff against working `main`
- [ ] Confirm no unintended dashboard/frontend files are included

## Release

- [ ] Freeze exact release commit
- [ ] Confirm proposed version
- [ ] Finalize release notes
- [ ] Final privacy/confidential-data sweep
- [ ] User approves tag/release
- [ ] Create tag and GitHub release
- [ ] Verify HACS install from released artifact
- [ ] User approves HACS default-store submission
- [ ] Submit to HACS

## Current prohibition

Do not merge the draft release PR, tag `0.9.0`, publish a GitHub release,
remove or rotate the working Sharp credentials, or submit to HACS while the
authentication architecture remains unresolved.
