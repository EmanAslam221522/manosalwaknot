# Production release checklist

A release is blocked until every applicable item is verified in staging with production-equivalent infrastructure.

## Mobile client

- `npm run verify` passes in CI.
- Android development and signed release builds launch without runtime module errors.
- Direct links redirect signed-out users to sign-in; signed-in users cannot reopen auth screens.
- Native tokens persist in SecureStore and are removed on logout/revocation. No tokens, OTPs, passwords, QR tokens, exact locations, report text, audio, or Mano messages appear in logs or analytics.
- Staging/production API origins use HTTPS and isolated data.
- TalkBack checks pass for sign-in, tabs, filters, permission denial, reservation, QR scanning, delivery transitions, and Mano confirmations.
- Slow, offline, timeout, 401/403/409/422/429/5xx, empty, cancellation, and retry states do not crash.
- Images are compressed, paginated/lazy loaded, and tested on mid-range Android hardware and constrained networks.
- Foreground location, camera, microphone, and notification permission denials preserve non-map/non-voice workflows.
- Notification foreground behavior and allowlisted deep links are tested. Push token rollover and logout revocation work.
- Analytics/crash monitoring has approved consent, masking, retention, environment/release tags, and PII scrubbing. Session replay remains disabled unless separately approved.

## FastAPI and data

- OpenAPI contract tests pass against mobile DTOs.
- Authentication rotation, revocation, OTP limits, role checks, and cross-user access tests pass.
- Concurrency test: with 10 servings, two concurrent reservations of 7 can never reserve 14; the excess request returns 409.
- Listing/reservation/delivery state-machine tests reject invalid transitions and record actor, previous/new state, timestamp, and request ID.
- QR tests cover expiry, unauthorized provider, wrong reservation, repeat scan, and concurrent scan.
- Report, verification, admin, and account-deletion retention/anonymization workflows are audited.
- PostGIS search validates coordinates/radius and never exposes unauthorized exact addresses.
- Upload tests reject oversized, malformed, mismatched MIME/extension, and unsafe image files.
- Mano tool authorization, prompt injection, private-data access, malformed output, rate limit, timeout, and provider outage tests pass. Core marketplace remains independent.
- Notification jobs, expiry jobs, cleanup, and AI-heavy work run outside request threads with failure/retry monitoring.

## Operations

- Development, staging, and production use separate databases, Redis, storage, secrets, push credentials, AI credentials, and API origins.
- Least-privilege service/DB accounts and encrypted connections are configured.
- Alembic migration, rollback/forward plan, lint, type checks, unit/integration/security tests, Docker build, dynamic `PORT` startup, and `/health` deployment gates pass.
- The selected provider supports and enables PostGIS and pgvector; PostgreSQL and Redis connections use TLS.
- Railway keeps PostgreSQL and Redis private and runs Alembic as a pre-deploy command.
- The Render/Neon/Upstash free staging option uses Neon's direct URL for Alembic, pooled URL for the API, and Upstash's `rediss://` TCP endpoint. Its cold starts and free quotas are accepted as non-production constraints.
- Error monitoring, structured logs, request IDs, latency/database/AI/push dashboards, and alerts are active without sensitive payload logging.
- Automated PostgreSQL backups have retention configured and a restoration drill has succeeded.
- Security headers, reverse proxy, TLS, CORS, rate limits, and administrative session controls are reviewed.
- Play Store privacy disclosures, data-safety form, permission rationale, signing, package ID, version code, icons, screenshots, and account-deletion path are complete.
