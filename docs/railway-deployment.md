# Railway deployment runbook

This runbook deploys the existing FastAPI backend to Railway and connects the Expo web and native test builds. It intentionally keeps PostgreSQL, Redis, JWT credentials, and the Groq key out of the mobile bundle.

## Production topology

Create one Railway project with three services in the same region:

1. **PostGIS + pgvector database** — use Railway's PostGIS/pgvector template, not its default PostgreSQL template. The current schema enables PostGIS and creates a geographic GiST index; the selected image also keeps pgvector available for later embedding features without a database migration.
2. **Redis** — use Railway's Redis template. Keep it private.
3. **API** — deploy this GitHub repository with **Root Directory** set to `/backend`. Railway detects `backend/Dockerfile` and `backend/railway.json` from that service root.

Do not give PostgreSQL or Redis public networking unless a short, controlled maintenance session requires it. Use persistent storage and enable database backups before production data is accepted.

## 1. Provision data services

In a new Railway project:

1. Add the [Postgres 18 + PostGIS + pgvector template](https://railway.com/deploy/postgres-18-postgis-pgvector-ssl-pitr-ready--postgres-18-postgis-pgvector-ssl-pitr-re).
2. Add Redis from **New → Database → Redis**.
3. Wait for both services to become healthy.
4. Confirm the database service exposes `DATABASE_URL` and Redis exposes `REDIS_URL` on Railway's private network.

Use separate Railway environments and separate data services for staging and production. Never point a staging build at production data.

## 2. Create the API service

1. Choose **New → GitHub Repo** and select this repository.
2. Set **Root Directory** to `/backend`.
3. Confirm Railway applies `backend/railway.json`. It selects `backend/Dockerfile`, runs `alembic upgrade head` before deployment, checks `/health` for up to 300 seconds, and restarts failed containers.
4. Keep one API replica for the first migration and smoke test. Scale only after the release checks pass.

If Railway does not detect Config as Code, enter the same values under **Settings → Deploy** rather than removing the migration or health gate.

The Docker image reads Railway's dynamic `PORT` and defaults to `8000` outside Railway.

## 3. Set API variables

Set these on the API service. Use Railway service-variable references for data-service URLs instead of copying credentials.

| Variable       | Value                                                                                     |
| -------------- | ----------------------------------------------------------------------------------------- |
| `ENVIRONMENT`  | `staging` for the first live test, then `production` for the production environment       |
| `DATABASE_URL` | Reference the private `DATABASE_URL` from the PostGIS service                             |
| `REDIS_URL`    | Reference the private `REDIS_URL` from Redis                                              |
| `JWT_SECRET`   | A new cryptographically random value of at least 32 characters                            |
| `CORS_ORIGINS` | `[]` initially; later set to a JSON array containing the exact published PWA HTTPS origin |
| `GROQ_API_KEY` | Backend-only Groq key                                                                     |
| `GROQ_MODEL`   | `llama-3.3-70b-versatile` unless another supported model is intentionally selected        |

Leave `OTP_DEBUG_CODE` unset. Never create `EXPO_PUBLIC_GROQ_API_KEY`, `EXPO_PUBLIC_DATABASE_URL`, `EXPO_PUBLIC_REDIS_URL`, or `EXPO_PUBLIC_JWT_SECRET`.

## 4. Deploy and generate the API domain

Deploy the API, then open **Settings → Networking → Generate Domain**. Railway creates an HTTPS address similar to:

```text
https://your-api-production.up.railway.app
```

Verify:

```sh
curl --fail https://your-api-production.up.railway.app/health
```

Expected response:

```json
{ "status": "ok" }
```

Production intentionally disables `/docs` and `/openapi.json`. Use staging for API documentation checks.

If deployment fails, check in this order:

1. Pre-deploy logs for PostGIS extension or migration errors.
2. API variables and private service references.
3. Start logs for configuration validation failures.
4. `/health` logs for database connectivity.

Do not bypass a failed migration or health check by removing the gate.

## 5. Publish the PWA

The API URL is public configuration and is embedded at build time. It is not a secret.

In Bilt, set the production web build environment to:

```env
EXPO_PUBLIC_APP_ENV=production
EXPO_PUBLIC_API_BASE_URL=https://your-api-production.up.railway.app
```

Open **Deploy & Share → Publish to web**. After Bilt provides the PWA HTTPS URL, return to Railway and set:

```env
CORS_ORIGINS=["https://your-pwa-domain.example"]
```

Redeploy the API, then test sign-in, discovery, reservations, QR/handover, volunteer delivery, notifications, and Mano from the published PWA. Any API URL change requires a new web export because `EXPO_PUBLIC_*` values are bundled at build time.

## 6. Create native test builds

Use the same live HTTPS API origin for the first Bilt-managed development/test builds:

```env
EXPO_PUBLIC_APP_ENV=staging
EXPO_PUBLIC_API_BASE_URL=https://your-api-production.up.railway.app
```

Open **Deploy & Share** and create real iOS/Android test builds. Native modules in this app require a development/custom build; Expo Go is not the production capability test environment. Keep staging and production build values separate before store submission.

For store release guidance, follow Bilt's [App Store guide](https://bilt.me/docs/guides/publish-to-app-store) and [Google Play guide](https://bilt.me/docs/guides/publish-to-google-play).

## 7. Release gates

Before accepting real users:

- Complete [`release-checklist.md`](release-checklist.md) against staging.
- Confirm PostgreSQL backups are enabled and perform a restoration drill.
- Verify PostGIS queries, migrations, API health, CORS, authentication refresh/revocation, role authorization, reservation concurrency, QR replay protection, delivery transitions, and Mano provider failure behavior.
- Add error monitoring and alerts without recording tokens, exact private locations, report text, audio, or Mano messages.
- Keep PostgreSQL and Redis private.
- Test rollback by redeploying the previous API image without reversing a destructive schema change.

## Account-authorized steps

Repository changes cannot create or bill Railway resources, connect your private GitHub account, generate the Railway domain, or submit signed native builds. Those steps require you to approve Railway and Bilt account prompts. Do not paste account passwords, database URLs, JWT secrets, or API keys into chat.
