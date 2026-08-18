# Authentication

Authentication uses server-side opaque bearer sessions. The API returns a random token once;
the database stores only its SHA-256 digest. This permits immediate logout, password-change
revocation, account disablement, and centrally controlled expiration without JWT revocation
lists or signing-key rollout.

## Passwords

- Passwords contain 12 to 128 Unicode characters.
- Passwords are hashed with `scrypt` using a random 16-byte salt and bounded work parameters.
- Stored hashes are parsed defensively so corrupted parameters cannot request unbounded memory.
- Login responses do not distinguish an unknown, disabled, locked, or incorrectly authenticated
  account.
- Missing accounts perform a dummy password verification to reduce timing-based enumeration.
- Consecutive failures lock the credential according to `AUTH_MAX_FAILED_ATTEMPTS` and
  `AUTH_LOCKOUT_MINUTES`.

Initial credentials are created through `AuthenticationService.set_password`. A protected
user-administration endpoint is intentionally deferred until organization/RBAC management is
available; no unauthenticated bootstrap endpoint exists.

## Sessions

- Tokens are generated with the operating system CSPRNG and sent as `Authorization: Bearer`.
- Raw tokens are never persisted.
- Sessions expire after `AUTH_SESSION_TTL_MINUTES` and can be revoked individually.
- Changing a password revokes every active session for that user.
- Disabled or soft-deleted users cannot log in and their existing sessions stop authenticating.
- Active memberships are returned by `/api/v1/auth/me`; disabled organizations are excluded.

Available endpoints:

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/change-password`

Bearer tokens must only be transported over HTTPS outside local development. Authentication
events will be copied into the formal audit trail during the audit/event phase. Redis or edge
rate limiting may supplement account lockout, but does not replace it.
