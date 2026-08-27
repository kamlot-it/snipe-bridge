# Publishing on GitHub

## Suggested repository metadata

**Name:** `snipe-bridge`

**Description:**

> Secure Docker bridge connecting Snipe-IT with legacy handheld barcode terminals for single and batch asset checkout and return.

**Topics:**

```text
snipe-it barcode-scanner asset-management inventory docker portainer
windows-ce openid-connect flask python self-hosted
```

Use `server/static/logo-default.png` as the project social-preview source. GitHub social previews are usually cropped; prepare a separate 1280×640 canvas from the same mark if desired.

## Before the first push

1. Replace any maintainer/contact placeholders in repository settings.
2. Enable **Issues**, **Discussions** if wanted, and **Private vulnerability reporting**.
3. Protect `main` and require the **Test** workflow.
4. Confirm `.env`, `data/`, databases, backups, and archives are not tracked.
5. Review `git status` and the staged diff for organization-specific names and hostnames.
6. Create the repository and push:

```bash
git init
git add .
git commit -m "Initial open-source release"
git branch -M main
git remote add origin git@github.com:OWNER/snipe-bridge.git
git push -u origin main
```

## Container publishing

The included `docker-publish.yml` workflow publishes multi-platform images to GitHub Container Registry after a tag beginning with `v` is pushed. It uses the repository owner/name automatically.

Create a release tag:

```bash
git tag -a v1.0.0-rc14 -m "Snipe Bridge 1.0.0-rc14"
git push origin v1.0.0-rc14
```

The resulting image is available as:

```text
ghcr.io/OWNER/REPOSITORY:1.0.0-rc14
```

Make the package public in GitHub's package settings if the repository policy requires it.

## Release checklist

- all tests pass;
- Docker image builds from the archive root;
- changelog contains the release;
- displayed `BUILD_VERSION` matches the tag;
- screenshots and documentation match the release;
- Compose and Portainer image tags match;
- no secrets or databases are present;
- release notes mention breaking configuration or migration requirements.
