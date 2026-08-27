# Administration and maintenance

## Settings ownership

The administrator panel stores managed settings in the application database. They are applied by all Gunicorn workers. Environment values seed a fresh installation, while local administrator credentials and runtime safety controls remain environment-only.

## Snipe-IT API account

Create a dedicated technical account/token. It needs enough access to:

- read hardware and individual assets;
- search/read users;
- read status labels;
- perform asset checkout and check-in.

Avoid using a personal administrator token. Record token ownership and rotation dates outside the repository.

## Status mappings

Open **Settings**, enter a valid Snipe-IT URL/token, and choose **Refresh status list**. The application reports success, warning, or failure in a temporary popup.

Select:

- **Checkout status** — applied after a successful checkout;
- **Ready status** — normal returned-to-stock state;
- **Service status** — return state for equipment requiring service.

These are Snipe-IT labels and are intentionally not translated. If a configured label is deleted or renamed in Snipe-IT, refresh and save the mapping again.

## Additional asset field

`SNIPEIT_CUSTOM_FIELD` accepts an optional Snipe-IT custom-field API/database key, not its display label. Leave it empty when no additional identifier is used. Asset Tag and serial-number lookup remain available.

## Branding and language

Administrators can set application name, organization, terminal title, primary/header colors, sign-in descriptions, and a logo. Accepted logo formats are PNG, JPEG, GIF, and WebP, up to 2 MB. The displayed logo is non-draggable and its context menu is suppressed in the UI, but any image delivered to a browser should still be considered publicly retrievable.

English and Polish are supported. A signed-in user's selection controls their panel and is propagated to the paired terminal. Unpaired sign-in and terminal pages have their own language selectors.

## Activity history

Regular operators see their own records. Administrators see all operators. The history supports:

- date, result, operation, asset, recipient, operator, and message filters;
- pick lists for bounded values and text fields for free-text columns;
- configurable page size and paging;
- CSV and XLSX exports localized to the viewing operator's language.

Result colors are semantic: success is green, warning/duplicate is yellow, and error is red.

![Activity history](images/logs.png)

## Database and backup

All persistent state belongs under `/data`:

- `bridge.db` — settings, terminal state, pair requests, and audit records;
- `branding/` — uploaded branding;
- `backups/` — rotating SQLite backups when configured.

Automatic backup is controlled by `DATABASE_BACKUP_DIR`, `DATABASE_BACKUP_INTERVAL_HOURS`, and `DATABASE_BACKUP_KEEP`. Also back up the complete Docker volume at the NAS/platform level.

To restore safely:

1. Stop the container.
2. Preserve the current `/data` directory as a rollback copy.
3. Replace `bridge.db` with a verified backup in the same volume.
4. Preserve ownership and permissions.
5. Start one container instance and verify `/healthz`, `/readyz`, login, and audit history.

Never copy a live SQLite database without using its backup mechanism or stopping all writers.

## Retention

`AUDIT_RETENTION_DAYS` and `TERMINAL_RETENTION_DAYS` remove old data during maintenance. Set either to `0` to disable its automatic expiry. Confirm your legal and operational retention requirements before changing these values.

## Health endpoints

- `/healthz` confirms that the application process can serve requests.
- `/readyz` confirms local readiness and, when `READINESS_CHECK_SNIPEIT=true`, includes an external Snipe-IT check.

Use `/readyz` for Docker health checks. Keep the external check disabled if a temporary Snipe-IT outage must not cause the container platform to restart a healthy bridge process.

## Routine checks

Monthly or after each update:

1. Verify automatic backups and test a restore in a non-production environment.
2. Review failed sign-ins, pairing errors, and Snipe-IT errors in Activity history.
3. Test checkout, return, batch mode, and session termination.
4. Confirm status mappings still exist.
5. Check the identity-provider client secret expiry.
6. Apply image and Python dependency security updates.
7. Confirm that the terminal endpoint remains restricted to its intended network.
