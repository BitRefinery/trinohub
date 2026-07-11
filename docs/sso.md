# Single sign-on (SSO)

TrinoHub can delegate authentication to any **OpenID Connect (OIDC)** provider
— Okta, Microsoft Entra ID, Google, or a generic OIDC server. Configure it from
the **Single sign-on (OIDC)** panel in **Settings** (requires
`MANAGE_SETTINGS`).

## How it works

TrinoHub uses the standard **authorization-code flow** as a confidential
client. When SSO is enabled, the sign-in screen shows a **Sign in with SSO**
button; clicking it sends the user to your identity provider and back. On
return, TrinoHub validates the ID token (issuer, audience, expiry, and a
per-login nonce) and signs the user in.

## Configuration

- **Issuer URL** — your provider's OIDC issuer, e.g.
  `https://login.example.com`. Must be `https://`.
- **Client ID / Client secret** — the credentials for the app you register
  with your provider. Leave the secret blank when editing to keep the stored
  one. Register TrinoHub's redirect URI —
  `https://<your-trinohub-host>/api/auth/oidc/callback` — with the provider.
- **Group claim** — the ID-token claim that carries the user's groups
  (default `groups`).
- **Group → role mappings** — one mapping per line, `idp-group = trinohub-role`.
  On every sign-in the user's TrinoHub roles are set from these mappings, so
  group membership in your IdP stays authoritative. Users in no mapped group
  get the **default role**.
- **Password login** — choose whether password sign-in stays available to
  **everyone** or is restricted to **operators only** (users holding a
  management privilege), so day-to-day users must use SSO while admins keep a
  break-glass password.

## Just-in-time provisioning

The first time someone signs in via SSO, TrinoHub creates their account
automatically with the roles their groups map to. They have **no password** and
can only sign in through the IdP. Deactivating the account in TrinoHub blocks
them regardless of the IdP.

## Sessions

Session lifetime is configurable from the **Sessions** panel in Settings (1 to
168 hours; default 12). Changing it affects new sign-ins. Use **Sign out
everywhere** to revoke all of your own active sessions at once — for example
after losing a device.
