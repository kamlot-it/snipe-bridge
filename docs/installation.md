# Installation

## Requirements

- a Docker-compatible host;
- network access from the container to Snipe-IT;
- a dedicated Snipe-IT API token with permission to read users, hardware, and status labels and to perform checkout/check-in;
- a modern browser for operators;
- HTTPS for any production operator panel exposed outside a trusted LAN.

The handheld only needs to reach `/terminal`. A Windows CE device may require plain HTTP on a trusted, isolated network because of its old TLS stack. Do not expose that endpoint directly to the internet.

## Docker Compose

Clone or unpack the repository, then create the runtime configuration:

```bash
cp .env.example .env
```

Generate a secret, for example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set at least:

```env
SECRET_KEY=generated-value
ADMIN_USERNAME=admin
ADMIN_PASSWORD=a-long-unique-password
SNIPEIT_BASE_URL=https://snipe.example.org
SNIPEIT_API_TOKEN=your-dedicated-token
SESSION_COOKIE_SECURE=true
```

Build and run:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f snipe-terminal-bridge
```

Open `https://bridge.example.org/` or, before configuring a proxy, `http://SERVER:8080/`.

## Minimal Compose file

```yaml
services:
  snipe-bridge:
    build: .
    image: snipe-bridge:1.0.0-rc14
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      SECRET_KEY: "replace-with-a-long-random-value"
      ADMIN_USERNAME: "admin"
      ADMIN_PASSWORD: "replace-with-a-strong-password"
      SNIPEIT_BASE_URL: "https://snipe.example.org"
      SNIPEIT_API_TOKEN: "replace-with-a-dedicated-token"
      DATABASE_PATH: "/data/bridge.db"
      LOGO_PATH: "/data/branding/logo"
      SESSION_COOKIE_SECURE: "false"
    volumes:
      - snipe_bridge_data:/data

volumes:
  snipe_bridge_data:
```

Change `SESSION_COOKIE_SECURE` to `true` when the public operator URL uses HTTPS.

## Portainer: build from the source archive

The supplied GitHub archive has `Dockerfile` at its root.

1. In Portainer, open **Images** and choose **Build a new image**.
2. Name it `snipe-terminal-bridge:1.0.0-rc14`.
3. Select **Upload** and provide the repository TAR/ZIP archive.
4. Keep **Dockerfile path** set to `Dockerfile`.
5. Build the image.
6. Open **Stacks → Add stack → Web editor**.
7. Paste `portainer-stack.yml`.
8. Add the required environment variables in Portainer's environment-variable section.
9. Deploy the stack.

If Portainer reports `Cannot locate specified Dockerfile: Dockerfile`, the archive was created with an extra parent directory. Upload the release source archive supplied with this project, or create an archive whose root contains `Dockerfile`, `requirements.txt`, and `server/`.

## Portainer with a registry image

After publishing an image, replace the local image line in `portainer-stack.yml`:

```yaml
image: ghcr.io/OWNER/snipe-bridge:1.0.0-rc14
```

Configure registry credentials in Portainer if the image is private.

## Synology NAS

Use Container Manager or Portainer. Keep the application data outside the container. A named volume works, but a bind mount makes backups easier to inspect:

```yaml
volumes:
  - /volume1/docker/snipe-bridge:/data
```

The directory must be writable by the container user (`nobody`, commonly UID/GID `65534`). If startup logs contain `PermissionError: [Errno 13] Permission denied`, correct ownership/permissions on that exact directory or use the named volume from the supplied Compose file. Do not run the whole container as root merely to hide a volume-permission problem.

## Reverse proxy and HTTPS

Forward the public hostname to container port `8080` and preserve `Host`, `X-Forwarded-Proto`, and the client address. Then set:

```env
TRUST_PROXY=true
SESSION_COOKIE_SECURE=true
OIDC_REDIRECT_URI=https://bridge.example.org/auth/oidc/callback
```

The redirect URI registered with the identity provider must match exactly, including scheme, hostname, path, and port.

## First-run checklist

1. Sign in with `ADMIN_USERNAME` and `ADMIN_PASSWORD`.
2. Open **Settings**.
3. Test the Snipe-IT connection.
4. Refresh the status list and select checkout, ready, and service statuses.
5. Configure the optional additional asset field.
6. Configure OpenID Connect and test with a non-admin operator.
7. Open `/terminal`, pair it, and test one checkout and one return.
8. Confirm the action in **Activity history**.
9. Back up `/data`.

## Updating

Back up `/data`, build or pull the new image, then recreate the container without deleting the volume:

```bash
docker compose build --pull
docker compose up -d
docker compose logs --tail=100 snipe-terminal-bridge
```

Never use `docker compose down -v` during a normal update; `-v` removes the persistent volume.
