# Configuration reference

Environment variables bootstrap a fresh installation. Settings saved in the administrator panel are stored in SQLite and take precedence over corresponding bootstrap values on subsequent requests. Local administrator credentials and low-level runtime controls remain environment-only.

Boolean values accept `1`, `true`, `yes`, or `on` as true; other values are false.

## Required bootstrap values

| Variable | Default | Description |
|---|---:|---|
| `SECRET_KEY` | unsafe development value | Flask signing key. Use at least 32 random bytes. |
| `ADMIN_USERNAME` | `admin` | Local fallback administrator username. |
| `ADMIN_PASSWORD` | empty | Local fallback administrator password. Required when secure configuration is enforced. |
| `SNIPEIT_BASE_URL` | empty | Snipe-IT root URL, without an API path. |
| `SNIPEIT_API_TOKEN` | empty | Dedicated Snipe-IT API token. Stored in `/data` if saved through Settings. |

Set `REQUIRE_SECURE_CONFIG=true` in production to reject obvious insecure bootstrap values.

## Application and branding

| Variable | Default | Description |
|---|---:|---|
| `APP_NAME` | `Snipe Bridge` | Application name in the browser UI. |
| `TERMINAL_TITLE` | `SNIPE BRIDGE` | Short terminal header, maximum 32 characters in the admin UI. |
| `ORGANIZATION_NAME` | `Your organization` | Organization shown on the sign-in screen. |
| `APP_LANGUAGE` | `en` | Bootstrap language: `en` or `pl`. Signed-in user and paired terminal preferences override it. |
| `LOGIN_DESCRIPTION_ENABLED` | `true` | Shows the configurable sign-in description. |
| `LOGIN_DESCRIPTION_PL` | Polish default | Polish sign-in description. |
| `LOGIN_DESCRIPTION_EN` | English default | English sign-in description. |
| `SHOW_IDENTITY_CONFIG_WARNING` | `true` | Shows the missing-identity-provider warning on sign-in. |
| `PRIMARY_COLOR` | `#FFCD05` | Main buttons and highlighted controls. |
| `HEADER_COLOR` | `#202124` | Header background. Success/accent green is intentionally fixed. |
| `LOGO_PATH` | `/data/branding/logo` | Persisted custom logo path prefix. |
| `DEVICE_LABEL` | `Scanner-01` | Bootstrap label used for a terminal context. |

## Snipe-IT

| Variable | Default | Description |
|---|---:|---|
| `SNIPEIT_BASE_URL` | empty | Root URL such as `https://snipe.example.org`. |
| `SNIPEIT_API_TOKEN` | empty | Bearer token used only by the server. |
| `SNIPEIT_CUSTOM_FIELD` | empty | Optional database/API key of an additional asset field. |
| `SNIPEIT_STATUS_CHECKOUT` | `Deployed` | Exact Snipe-IT status assigned after checkout. |
| `SNIPEIT_STATUS_READY` | `Ready to Deploy` | Exact default status after return. |
| `SNIPEIT_STATUS_SERVICE` | `Pending` | Exact service-required status after return. |
| `REQUEST_TIMEOUT_SECONDS` | `12` | HTTP timeout for Snipe-IT requests. |
| `STATUS_CACHE_SECONDS` | `300` | Status-label cache lifetime. |
| `VERIFY_TLS` | `true` | Verifies the Snipe-IT TLS certificate. Disable only for a controlled test environment. |
| `READINESS_CHECK_SNIPEIT` | `false` | Makes `/readyz` include a live Snipe-IT check. |

Status names are installation-specific. Use **Refresh status list** in Settings and select the values returned by your Snipe-IT server.

## OpenID Connect

| Variable | Default | Description |
|---|---:|---|
| `IDENTITY_PROVIDER_TYPE` | `generic` | UI preset/provider type. |
| `IDENTITY_PROVIDER_NAME` | `Identity Provider` | Name shown on the sign-in button. |
| `OIDC_DISCOVERY_URL` | empty | Provider `.well-known/openid-configuration` URL. |
| `OIDC_CLIENT_ID` | empty | OAuth/OIDC client ID. |
| `OIDC_CLIENT_SECRET` | empty | OAuth/OIDC client secret. |
| `OIDC_REDIRECT_URI` | empty | Exact callback, normally `https://HOST/auth/oidc/callback`. |
| `IDENTITY_ALLOWED_DOMAINS` | empty | Optional comma, semicolon, or space-separated e-mail domains. |
| `OIDC_SCOPES` | `openid profile email` | Requested scopes. |
| `OIDC_EMAIL_CLAIM` | `email` | Claim containing the operator e-mail. |
| `OIDC_GROUPS_CLAIM` | `groups` | Claim containing group membership. |
| `OIDC_ADMIN_GROUPS` | empty | Groups receiving administrator access. |
| `ADMIN_EMAILS` | empty | E-mail addresses receiving administrator access. |

Legacy `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_ALLOWED_DOMAIN`, and `GOOGLE_REDIRECT_URI` are accepted for compatibility, but new deployments should use the generic OIDC variables.

`ADMIN_PIN` is also recognized as a legacy fallback setting. New deployments should configure `ADMIN_USERNAME` and `ADMIN_PASSWORD` instead.

## Terminal and pairing

| Variable | Default | Description |
|---|---:|---|
| `PAIR_TTL_MINUTES` | `15` | Six-digit manual pairing-code lifetime. |
| `QR_PAIR_TTL_MINUTES` | `2` | Single-use QR pairing-token lifetime; minimum effective value is 1 minute. |
| `TERMINAL_IDLE_MINUTES` | `15` | Ends an inactive terminal session; `0` disables idle expiry. |
| `TERMINAL_COOKIE_SECURE` | `false` | Sends the terminal cookie only over HTTPS. Keep false only when a legacy terminal must use trusted-LAN HTTP. |
| `TERMINAL_SAFE_MODE` | `false` | Uses the reduced legacy-safe terminal frontend. |
| `ASSET_IMAGES_ENABLED` | `true` | Loads available asset/category images. Disable for slow or unstable terminals. |
| `PAIR_MAX_ATTEMPTS` | `10` | Pairing attempts allowed per rate-limit window. |
| `PAIR_WINDOW_SECONDS` | `300` | Pairing rate-limit window. |
| `PAIR_BLOCK_SECONDS` | `600` | Pairing block duration after the limit is exceeded. |
| `TERMINAL_OPERATION_LOCK_SECONDS` | `120` | Prevents duplicate concurrent confirmation of one terminal operation. |

## Sessions, proxy, and login protection

| Variable | Default | Description |
|---|---:|---|
| `TRUST_PROXY` | `false` | Trusts forwarded proxy headers. Enable only behind a configured reverse proxy. |
| `SESSION_COOKIE_SECURE` | `false` | Sends operator session cookies only over HTTPS. Set true in production. |
| `CSRF_ENABLED` | `true` | Enables CSRF protection on state-changing browser forms. |
| `LOGIN_MAX_ATTEMPTS` | `5` | Local-login attempts per window. |
| `LOGIN_WINDOW_SECONDS` | `300` | Local-login rate-limit window. |
| `LOGIN_BLOCK_SECONDS` | `900` | Local-login block duration. |
| `REQUIRE_SECURE_CONFIG` | `false` | Rejects unsafe production bootstrap configuration. Recommended: true. |

Operator session cookies are HTTP-only and use `SameSite=Lax`.

## Database, retention, and backups

| Variable | Default | Description |
|---|---:|---|
| `DATABASE_PATH` | `data/bridge.db` in source; `/data/bridge.db` in image | SQLite file. |
| `SQLITE_BUSY_TIMEOUT_SECONDS` | `10` | Wait time for a busy database. |
| `SQLITE_WAL_ENABLED` | `true` | Enables write-ahead logging for concurrent workers. |
| `AUDIT_RETENTION_DAYS` | `365` | Audit retention; `0` disables automatic expiry. |
| `TERMINAL_RETENTION_DAYS` | `90` | Old terminal-record retention; `0` disables automatic expiry. |
| `DATABASE_BACKUP_DIR` | empty | Backup directory. `.env.example` uses `/data/backups`. |
| `DATABASE_BACKUP_INTERVAL_HOURS` | `24` | Automatic backup interval; `0` disables automatic backup. |
| `DATABASE_BACKUP_KEEP` | `7` | Number of rotating backups retained, minimum 1. |

## Container-only variable

| Variable | Default | Description |
|---|---:|---|
| `PORT` | `8080` | Host port used by Compose. Gunicorn listens on container port 8080. |

## Persistence and precedence

The `/data` volume contains the database, uploaded branding, and backups. Saving a value in **Settings** changes the database-backed effective configuration for all Gunicorn workers. Changing the same environment variable later may not replace that saved value. Update or clear it in Settings, or start with a fresh volume when deliberately creating a new installation.

The Snipe-IT token and OIDC client secret are masked in Settings. Leaving a masked secret unchanged preserves it; use the explicit removal control to clear a stored Snipe-IT token.
