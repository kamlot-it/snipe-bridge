# Authentication and OpenID Connect

Snipe Bridge supports two operator entry paths:

1. OpenID Connect for normal users and administrators.
2. A local username/password administrator as a controlled fallback.

An OIDC e-mail must match an active user in Snipe-IT. This maps the authenticated person to the operator recorded in the activity history.

## Local administrator

Configure environment-only credentials:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=a-long-unique-password
```

Do not share this account with ordinary operators. Rotate it in the container configuration and recreate the container. A successful local login is audited as a username/password administrator sign-in.

## Generic OIDC configuration

```env
IDENTITY_PROVIDER_TYPE=generic
IDENTITY_PROVIDER_NAME=Company SSO
OIDC_DISCOVERY_URL=https://id.example.org/.well-known/openid-configuration
OIDC_CLIENT_ID=snipe-bridge
OIDC_CLIENT_SECRET=replace-with-client-secret
OIDC_REDIRECT_URI=https://bridge.example.org/auth/oidc/callback
IDENTITY_ALLOWED_DOMAINS=example.org
OIDC_SCOPES=openid profile email
OIDC_EMAIL_CLAIM=email
OIDC_GROUPS_CLAIM=groups
OIDC_ADMIN_GROUPS=snipe-bridge-admins
ADMIN_EMAILS=owner@example.org
```

The provider must allow the redirect URI exactly as configured. If the bridge sits behind a reverse proxy, set `TRUST_PROXY=true` and make sure the proxy sends the original HTTPS scheme.

## Google Workspace

Create an OAuth 2.0 Web application and register:

```text
https://bridge.example.org/auth/oidc/callback
```

Use:

```env
IDENTITY_PROVIDER_TYPE=google
IDENTITY_PROVIDER_NAME=Google Workspace
OIDC_DISCOVERY_URL=https://accounts.google.com/.well-known/openid-configuration
OIDC_CLIENT_ID=your-client-id.apps.googleusercontent.com
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=https://bridge.example.org/auth/oidc/callback
IDENTITY_ALLOWED_DOMAINS=example.org
```

The domain filter validates the e-mail returned by the provider. It does not create users in Snipe-IT; the same e-mail must already exist there.

## Microsoft Entra ID

For a tenant-specific application, prefer the tenant ID instead of `common`:

```env
IDENTITY_PROVIDER_TYPE=entra
IDENTITY_PROVIDER_NAME=Microsoft Entra ID
OIDC_DISCOVERY_URL=https://login.microsoftonline.com/TENANT-ID/v2.0/.well-known/openid-configuration
OIDC_CLIENT_ID=your-application-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=https://bridge.example.org/auth/oidc/callback
```

If group administration is enabled, ensure the token/user-info response contains the configured groups claim. Large Entra group memberships may require provider-specific handling; in that case, use `ADMIN_EMAILS` as the reliable fallback.

## Keycloak, Authentik, Okta, and others

Use the discovery document published by the provider, request `openid profile email`, and ensure the selected e-mail claim contains a verified address. Set `OIDC_EMAIL_CLAIM` or `OIDC_GROUPS_CLAIM` when the provider uses different claim names.

## Administrator mapping

An OIDC user receives administrator access when either condition is true:

- their normalized e-mail is listed in `ADMIN_EMAILS`; or
- one of their groups matches `OIDC_ADMIN_GROUPS`.

Administrators can view all users' activity history and open Settings. Regular users only see their own actions.

## Sign-out behavior

Signing out of the operator panel ends the operator session and resets its paired terminal session. The terminal returns to the pairing screen. This does not necessarily end the upstream provider's global browser session.

## Security checklist

- keep the client secret out of Git and Compose files committed to Git;
- use HTTPS for operator/OIDC traffic;
- restrict accepted domains when appropriate;
- configure a small administrator group;
- retain and periodically test the local fallback account;
- review sign-in events in Activity history;
- rotate the client secret according to provider policy.
