# Development

## Local environment

Snipe Bridge targets Python 3.12.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
pytest
```

For local development:

```bash
flask --app server.app run --debug
```

Use only test credentials and a non-production Snipe-IT instance while developing.

## Project layout

```text
server/app.py              Flask application and routes
server/storage.py          SQLite persistence, locking, retention, backup
server/snipe.py            Snipe-IT REST client and asset lookup
server/localization.py     Polish/English translation catalog
server/templates/          Operator and terminal templates
server/static/             CSS, logo, and favicon
tests/                     Unit and regression tests
docs/                      User and administrator documentation
```

## Tests

Run the complete suite:

```bash
pytest
```

The regression suite covers, among other behavior:

- clean first boot and concurrent schema initialization;
- pairing and mode changes;
- complete QR/barcode submission on legacy clients;
- `/hardware/<ID>` extraction independent of hostname;
- terminal focus and MC31xx green/red keys;
- operator and terminal localization in Polish and English;
- batch quantity grammar and protected Snipe-IT field names;
- secure masking of stored tokens and secrets.

When adding user-facing text, update the localization catalog and add a rendered-language assertion for both languages. Do not translate Snipe-IT values such as status names, Asset Tag, serials, e-mail addresses, or user-provided asset data.

## Legacy terminal constraints

The terminal frontend is intentionally not a modern single-page application. Preserve:

- a fixed narrow layout without horizontal document scrolling;
- server-rendered fallbacks;
- minimal JavaScript and memory use;
- automatic scan-field focus;
- scanner Enter handling only after complete input;
- green/red hardware-key behavior;
- ordinary document refresh where old browser engines are unstable with partial updates;
- no dependency on modern JavaScript frameworks.

Test changes in both a current browser and the actual legacy device whenever possible. A desktop responsive emulator is not a substitute for the Windows CE browser engine.

## Docker verification

The `Test` workflow runs the suite on Python 3.12 and 3.14. It also builds
and starts the production Gunicorn command on both `linux/amd64` and
`linux/arm64` for each Python version. HTTP checks cover health, storage
readiness, login and the terminal pairing page. Snipe-IT is not contacted;
these checks use disposable CI credentials and a fresh container database.

The workflow checks release tag generation using both a stable and an RC
version. Test images are loaded locally on the runner and are not published.
The default production image remains Python 3.12. To test another version:

```bash
docker build --build-arg PYTHON_VERSION=3.14-slim -t snipe-bridge:test .
```

After starting a test container as below, check it from a second terminal:

```bash
python3 scripts/smoke_http.py http://127.0.0.1:8080
```

Image regression tests check QR SVG generation and PNG/JPEG conversion for
terminal thumbnails. They do not verify QR readability on a physical scanner.
Before releasing dependency updates, also check a complete scan and confirmation
on the handheld, plus authentication through the deployment's reverse proxy.

```bash
docker build -t snipe-bridge:test .
docker run --rm -p 8080:8080 \
  -e SECRET_KEY=test-only-long-secret \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=test-only-password \
  -e SNIPEIT_BASE_URL=https://snipe.example.org \
  -e SNIPEIT_API_TOKEN=test-only-token \
  -e REQUIRE_SECURE_CONFIG=false \
  snipe-bridge:test
```

Do not publish a test image containing embedded secrets. Runtime environment variables are not part of the image unless explicitly added during build.

## Pull requests

Keep changes focused, add tests, update the changelog for user-visible behavior, and describe manual terminal verification. See [CONTRIBUTING.md](../CONTRIBUTING.md).
