# Authentication Distribution Research

This document records release-blocker research only. It does not change the
working authentication implementation.

## Current blocker

The working integration relies on application authentication material recovered
from the official Sharp Kitchen application, including a Cognito application
client credential and a shared mTLS client certificate/private key. The formal
HACS release must not embed the extracted private key.

## Options under consideration

### 1. User-provided Sharp application credential + user-provided mTLS PEM files

Home Assistant can store user-entered OAuth client ID/client secret values
through its Application Credentials framework. The mTLS certificate/private key
would still need a separate mechanism, such as paths under the Home Assistant
configuration directory or values entered during a setup/reconfigure flow.

Pros:
- public repository contains no extracted private key;
- no hosted relay service;
- closest to normal local secret management.

Cons:
- ordinary Sharp users do not appear to have a supported developer portal for
  creating their own Sharp Kitchen OAuth client;
- obtaining the same vendor-app credentials and mTLS private key currently
  requires reverse-engineering/extraction work and is not a realistic normal
  installation experience.

### 2. User-supplied credential bundle produced by a separate extraction helper

Keep extracted credential material out of the HACS repository. A separate tool
could produce a local bundle that the integration imports.

Pros:
- HACS repository remains credential-free;
- integration setup could validate the bundle before saving paths/material.

Cons:
- extraction of the mTLS private key remains technically difficult;
- the current research indicates the app's bundled PKCS#12 material is not a
  simple user-exportable credential;
- adds a substantial prerequisite and support burden.

### 3. Supported Sharp provisioning/pairing flow that generates per-installation mTLS credentials

This is the preferred architecture if Sharp exposes such a flow.

Pros:
- cleanest security model;
- no shared private key distribution;
- comparable to integrations that pair and generate/store a unique client
  certificate for each Home Assistant installation.

Cons:
- no such Sharp provisioning endpoint has been identified yet;
- requires further protocol research before it can be considered viable.

### 4. User-provided certificate/key files obtained independently

The integration would accept certificate and private-key paths or pasted PEM
material, but would not prescribe or automate extraction.

Pros:
- technically straightforward for the Home Assistant integration;
- public repository stays free of the private key.

Cons:
- poor user experience;
- most users cannot realistically obtain the material;
- support/documentation would still need to address how legitimate users obtain
  it.

### 5. Project-operated relay/proxy service holding the shared mTLS key

Home Assistant would authenticate users locally, but Sharp API calls requiring
mTLS would transit a service controlled by the project.

Pros:
- HACS package contains no Sharp private key;
- easiest end-user setup.

Cons:
- creates a new hosted service, operating cost, privacy/security responsibility,
  availability dependency, and trust boundary;
- routes appliance/account traffic through a third party;
- not recommended for this project unless all direct-client approaches fail.

## Home Assistant Application Credentials

Application Credentials is suitable for storing/selecting a user-provided
OAuth client ID and client secret. It does not store or provision a TLS client
certificate/private key.

Sharp also uses a hosted-login flow tied to the official application's OAuth
client/redirect behavior. Application Credentials therefore does not, by
itself, make the current Sharp login flow a standard Home Assistant OAuth flow.
A separate compatibility investigation is required before refactoring login to
Home Assistant's OAuth helpers.

## Additional provisioning research

Public Sharp material reviewed during release preparation continues to direct
SMD2489ES users through the Sharp Kitchen app for appliance pairing. The
published pairing flow covers Wi-Fi/app/account pairing but does not document
issuance of a new client TLS certificate or private key to third-party clients.

Sharp also publishes an Alexa account-linking path using the user's Sharp
account. This proves that Sharp supports account linking outside the mobile app,
but it does not expose a public device-control API, a user-created OAuth client,
or a per-installation mTLS credential flow that Home Assistant could currently
reuse.

Public GitHub/code searches for the Sharp Kitchen backend host, API path,
application package, and bundled PKCS#12 filename did not uncover an independent
implementation or a documented certificate-registration endpoint.

### Best viable public-safe fallback at this checkpoint

If no Sharp provisioning endpoint is discovered, the most practical direct
client design is:

1. Remove vendor-app secrets/key material from the future public release only
   after a tested replacement exists.
2. Let the user supply OAuth application values locally.
3. Store/select the OAuth client ID and client secret through Home Assistant
   Application Credentials where compatible with Sharp's hosted-login behavior.
4. Let the user supply the mTLS certificate and private key as local files,
   preferably under `/config/sharp_kitchen/`.
5. Store only file paths/references in the config entry, not private-key text.
6. Validate certificate/key parsing and matching during setup/reconfigure.
7. Keep extraction/import outside the HACS package, ideally through a separate
   local helper if a repeatable extraction method can be made practical.

This is not as user-friendly as true vendor provisioning, but it keeps the HACS
repository free of the extracted private key and avoids a project-operated
cloud relay.

## Current recommendation

Do not change the working integration yet.

Research in this order:

1. Determine whether the Sharp backend/app has an undocumented supported
   registration/provisioning operation capable of issuing a new client
   certificate/key or otherwise removing the need for the shared app key.
2. If not, prototype a credential-free public integration that accepts
   user-supplied client ID/secret and mTLS certificate/key material without
   committing those values.
3. Evaluate whether a separate extraction/import helper can make that
   user-supplied model realistic.
4. Treat a hosted relay as a last resort.

No release, merge, tag, or HACS submission is authorized by this document.
