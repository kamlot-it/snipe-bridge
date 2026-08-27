# Troubleshooting

Start with the container logs and health endpoints:

```bash
docker compose ps
docker compose logs --tail=200 snipe-terminal-bridge
curl -fsS http://127.0.0.1:8080/healthz
curl -fsS http://127.0.0.1:8080/readyz
```

Never paste an API token, OIDC client secret, administrator password, session cookie, or complete production database into a public issue.

## Container does not start: permission denied for `data`

Example:

```text
PermissionError: [Errno 13] Permission denied: 'data'
```

The container cannot create or write the configured SQLite parent directory. The supplied image expects:

```env
DATABASE_PATH=/data/bridge.db
LOGO_PATH=/data/branding/logo
```

Use the supplied named `/data` volume. For a Synology bind mount, make the exact host directory writable by the container user (commonly UID/GID `65534`) before starting the container. Verify that Portainer did not override `DATABASE_PATH` with the relative value `data/bridge.db`.

## Portainer cannot locate `Dockerfile`

Example:

```text
Unable to build image: Cannot locate specified Dockerfile: Dockerfile
```

The build archive has an extra directory level or the configured Dockerfile path is wrong. At the archive root, Portainer must see:

```text
Dockerfile
requirements.txt
server/
```

Use the release source archive or set the Dockerfile path to the real path inside the uploaded archive.

## Worker failed to boot

Find the first traceback before Gunicorn's final `Worker failed to boot` line. Common causes are:

- unwritable database directory;
- invalid numeric environment values;
- an incompatible/corrupt existing SQLite file;
- an unsafe configuration rejected by `REQUIRE_SECURE_CONFIG=true`.

Do not delete the data volume to make the error disappear. Back it up first, then correct the specific cause.

## Missing checkout/ready/service status

The configured label does not exactly match a Snipe-IT status. In **Settings**:

1. test the Snipe-IT connection;
2. choose **Refresh status list**;
3. select all three statuses from the returned lists;
4. save settings.

Also verify that the technical API account can read status labels.

## Snipe-IT connection test fails

Check:

- the base URL contains the installation root, not `/api/v1`;
- the token belongs to an active Snipe-IT account;
- the container can resolve and reach the hostname;
- the certificate is valid for the hostname;
- the reverse proxy does not block API requests;
- `VERIFY_TLS` remains true unless you deliberately use a private test PKI.

Run a network test from the Docker host or a temporary container without printing the token to shared logs.

## Identity-provider login is unavailable

All four values are needed: discovery URL, Client ID, Client Secret, and exact callback URL. Confirm that the provider registration contains:

```text
https://bridge.example.org/auth/oidc/callback
```

If the provider reports a redirect mismatch, compare scheme, host, path, and port character by character. Behind a proxy, enable `TRUST_PROXY=true` and forward the original HTTPS scheme.

If authentication succeeds but access is denied, verify:

- the provider returned the configured e-mail claim;
- the e-mail is verified;
- its domain is allowed, if restrictions are enabled;
- the same e-mail belongs to an active Snipe-IT user.

## Pairing QR expired or was already used

Pairing QR tokens are deliberately short-lived and single-use. Generate a new QR in the operator panel and scan it once. Check that both hosts have reasonably synchronized clocks. A manual six-digit code remains available as fallback.

If a valid-looking QR intermittently fails, verify that the terminal scans the complete token and sends its trailing Enter. Test at close range and disable scanner transformations that strip URL characters.

## Asset QR is reported as not found

Snipe Bridge recognizes a numeric ID from any scanned `/hardware/<ID>` segment, regardless of hostname. A valid example is:

```text
https://snipe.example.org/hardware/64
```

If the error shows only part of the URL:

- verify that the scanner appends Enter only after the complete code;
- disable prefix/suffix transformations other than the final Enter;
- ensure no browser autocomplete replaces the field;
- test the same QR in a plain text editor on the terminal;
- confirm that asset ID exists and is visible to the API account.

Builds `rc8`–`rc13` include specific fixes for long legacy-browser input and `/hardware/<ID>` normalization. Confirm the build displayed at the bottom of the terminal.

## Scan requires a second attempt

The terminal waits for scanner input to stop changing before it submits. Configure the scanner to send Enter, keep focus in the scan field, and avoid touching the page during a scan. If a non-interactive page click removes focus, update to the current build; focus restoration is covered by regression tests.

## Terminal does not change mode

Mode selection is sent from the operator panel and the terminal refreshes to a cache-busted document. Wait for the short loading state. If one manual refresh loads the correct mode, inspect reverse-proxy caching and disable caching for `/terminal` and terminal status routes.

Do not use an HTML accelerator, service worker, or proxy rule that caches terminal pages.

## Legacy terminal browser crashes

Old Windows CE engines have limited memory. Try:

```env
TERMINAL_SAFE_MODE=true
ASSET_IMAGES_ENABLED=false
```

Restart the container, end the old session, and pair again. Also close other terminal applications and remove browser plugins/toolbars. Safe mode intentionally sacrifices some dynamic behavior for stability.

## Wrong or stretched asset image

Disable asset images to confirm the cause. Images are rendered with their original aspect ratio, but a stale proxy/browser cache can still show an earlier response. Disable proxy caching for image routes and begin a fresh terminal session.

## Horizontal scrolling or clipped terminal text

The terminal UI targets 320 px. Confirm that the browser is not applying zoom and that the terminal is receiving the terminal stylesheet, not the operator view. Long category and error text should wrap without splitting the entire layout. Include a photo, exact displayed build, language, and route in a bug report.

## Duplicate batch item

A duplicate scan is a warning and must not add a second list item. If it does, record both raw code values—they may differ because one is an Asset Tag and one is a hardware URL for the same asset—and open an issue.

## Database is locked

Keep `SQLITE_WAL_ENABLED=true` and do not mount the database on a filesystem with unreliable SQLite locking. Increase `SQLITE_BUSY_TIMEOUT_SECONDS` modestly if storage is slow. Run a single application service sharing one local `/data` volume; SQLite is not intended for multiple independent hosts.

## Information to include in a support request

- Snipe Bridge version/build;
- deployment method and Docker/Portainer version;
- terminal model, OS, and browser;
- operator and terminal language;
- exact route and workflow mode;
- sanitized error text and relevant log traceback;
- whether a manual refresh changes the result;
- reproduction steps using non-sensitive test asset IDs.
