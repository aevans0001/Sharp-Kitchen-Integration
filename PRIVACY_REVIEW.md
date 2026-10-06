# Privacy and Confidential-Information Review

Last reviewed: 2026-10-06 (after temporary branding addition)

Scope: release/hacs-readiness tracked release-preparation files and repository
metadata prepared for the future Sharp Kitchen 0.9.0 release.

## Personal-information sweep

No release-preparation file introduced:

- personal email addresses;
- home/street addresses;
- IPv4 addresses;
- MAC addresses;
- Windows user-profile paths;
- UNC/network paths;
- personal credentials, refresh tokens, or account-specific identifiers.

Release-preparation commits expose the GitHub account identity through normal
Git commit metadata; no personal email address was returned by the connected
GitHub tooling.

A fresh scan of the full PR diff after adding the temporary brand icon found
no personal email addresses, IP addresses, MAC addresses, local user paths,
street address, personal name, bearer tokens, or AWS-style access keys in the
release-preparation changes.

## Known intentional authentication material in the preserved working code

The pre-existing working integration still contains Sharp application
authentication material recovered from the official application, including the
Cognito application credential and shared mTLS certificate/private-key
material.

This material is the explicit hard blocker for formal HACS release. It was not
introduced by the HACS-readiness work and has not been removed, rotated, or
modified because doing so would break the preserved working implementation.

## Release rule

Repeat this review after any future authentication-architecture change and
before freezing the release commit. No tag, merge, release, or HACS submission
is authorized by this review.
