# Contributing to Snipe Bridge

Thank you for helping improve Snipe Bridge. Bug reports, compatibility findings, translations, documentation, and focused pull requests are welcome.

## Before opening an issue

1. Search existing issues and the [troubleshooting guide](docs/troubleshooting.md).
2. Confirm the problem on the newest release.
3. Remove secrets and personal data from screenshots and logs.
4. For terminal bugs, include the model, OS/browser, displayed build, language, and exact scan/mode sequence.

Report security problems privately according to [SECURITY.md](SECURITY.md).

## Development setup

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

See [docs/development.md](docs/development.md) for project structure, Docker verification, and legacy-terminal constraints.

## Pull-request rules

- create a focused branch from `main`;
- keep unrelated formatting or refactoring out of the change;
- add or update tests for behavior changes;
- run the complete `pytest` suite;
- update documentation and `CHANGELOG.md` for user-visible changes;
- never commit `.env`, databases, archives, production logs, credentials, or organization-specific branding;
- preserve the fixed narrow terminal layout and old-browser compatibility;
- verify both Polish and English for every new user-facing message;
- describe manual checks performed on a real terminal, when relevant.

Keep translations in the localization catalog. Do not translate dynamic Snipe-IT data, status-label values, Asset Tag, serial numbers, names, e-mails, or raw user input. Add a regression assertion that renders the affected view in both supported languages.

By contributing, you agree that your contribution is licensed under the project's [MIT License](LICENSE).
