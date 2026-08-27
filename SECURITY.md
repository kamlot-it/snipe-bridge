# Security policy

## Supported versions

Security fixes are provided for the newest published release candidate or stable release.

| Version | Supported |
|---|---|
| Latest release | Yes |
| Older builds | No |

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private vulnerability reporting feature when enabled, or contact the repository maintainer through the private channel listed in the repository profile.

Include the affected version and deployment method, impact, minimal reproduction, relevant sanitized logs, and any suggested mitigation. Do not include real API tokens, client secrets, passwords, session cookies, personal data, or a production database. Allow the maintainer reasonable time to investigate and release a fix before public disclosure.

## Deployment assumptions

Snipe Bridge is a server-side security boundary between a legacy terminal and Snipe-IT. Operators must:

- use HTTPS for the operator panel and OIDC callback;
- keep the terminal endpoint on a trusted, restricted network;
- use a dedicated least-privilege Snipe-IT API account;
- generate a unique `SECRET_KEY` and administrator password;
- protect the `/data` volume and its backups;
- keep `VERIFY_TLS=true` in production;
- enable `SESSION_COOKIE_SECURE=true` behind HTTPS;
- review activity history and rotate credentials regularly.

Pairing QR tokens are short-lived and single-use. They contain no Snipe-IT API token. A custom logo delivered to a browser must not be treated as confidential even though dragging and the context menu are disabled in the UI.
