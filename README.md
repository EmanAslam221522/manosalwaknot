# ManOSalwaKnot mobile client

Production-oriented React Native and Expo client for the ManOSalwaKnot food-rescue platform. The app is an HTTPS client for a separate FastAPI service; it never connects directly to PostgreSQL, Redis, object storage, maps administration APIs, or an AI provider.

## Architecture

- Expo Router and TypeScript
- HeroUI Native and Uniwind design system
- TanStack Query for server state
- Zod validation at API boundaries
- Expo SecureStore for native session tokens; web sessions are memory-only
- Centralized `/api/v1` client with timeout, cancellation, safe GET retries, rotating refresh tokens, normalized errors, and request correlation IDs
- Server-authoritative roles, quantities, state transitions, QR handover, verification, impact, and Mano actions

No food listing, reservation, impact number, or organization is hardcoded as production data.

## Setup

Requirements: Node.js 20.19.4 or newer and npm 10. Native development also requires the Android/iOS platform toolchain or a Bilt-managed development build.

```sh
cp .env.example .env.local
npm ci
npx expo start
```

Set `EXPO_PUBLIC_API_BASE_URL` to the FastAPI origin. Public Expo variables are embedded in the client bundle and must never contain database credentials, JWT secrets, Groq keys, private maps keys, storage keys, or push-service secrets.

Configured native modules include SecureStore, foreground location, camera/QR scanning, microphone recording, notifications, and native maps. Rebuild the native application after plugin or permission changes. Expo Go should not be treated as the production-capability test environment.

## Environments

`EXPO_PUBLIC_APP_ENV` accepts only `development`, `staging`, or `production`. Staging and production require HTTPS. Use separate API origins and data stores for every environment.

Optional PostHog web analytics uses `EXPO_PUBLIC_POSTHOG_KEY` and `EXPO_PUBLIC_POSTHOG_HOST`. URL-query configuration and session recording are disabled. Leave both unset until privacy, consent, retention, and data-scrubbing requirements are approved.

## Commands

```sh
npm test             # mobile boundary unit tests
npm run lint         # lint and TypeScript checks
npm run expo-check   # Expo dependency compatibility
npm run verify       # complete CI verification
npm run android      # native Android development build
npm run ios          # native iOS development build
npm run build:pwa    # web/PWA export
```

## Railway production deployment

The production API is designed to run as a private-service stack on Railway: a Docker-based FastAPI service, a PostGIS-capable PostgreSQL service, and Redis. Follow [`docs/railway-deployment.md`](docs/railway-deployment.md) for provisioning, variables, migrations, health checks, generated HTTPS domain, PWA publishing, and native test-build configuration.

Do not use the default Railway PostgreSQL template for this app. The current schema requires PostGIS, and the selected PostGIS + pgvector image also supports later embedding features; enable persistent storage and backups. Database, Redis, JWT, and Groq credentials stay in Railway and must never be copied into `EXPO_PUBLIC_*` variables.

## Local FastAPI backend

The backend lives in `backend/` and uses FastAPI, PostgreSQL/PostGIS, Redis, SQLAlchemy, Alembic, and backend-only Groq access. Docker Compose supplies safe local defaults; do not reuse them outside development.

```sh
# Optional: place local overrides such as GROQ_API_KEY in the repository-root .env.
# Never commit that file.
docker compose up --build
curl http://localhost:8000/health
```

The API is available at `http://localhost:8000`, OpenAPI at `http://localhost:8000/docs`, and the mobile development value should be `EXPO_PUBLIC_API_BASE_URL=http://localhost:8000` (use the host machine's LAN address on a physical device).

Run backend checks from the backend directory:

```sh
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy app
pytest --cov=app --cov-fail-under=80
alembic upgrade head
```

For a clean local database, stop the stack and explicitly remove development volumes with `docker compose down -v`, then start it again. This permanently deletes local data. Production requires externally managed secrets, HTTPS, trusted-proxy rate limiting, backups, monitoring, and an independently reviewed deployment configuration.

## Backend contract

See [`docs/backend-contract.md`](docs/backend-contract.md). It lists required endpoints and server-owned guarantees. FastAPI OpenAPI remains the authoritative API specification and should be contract-tested against the Zod DTOs in `services/`.

Provider listing creation remains intentionally unavailable in the UI until the backend supplies authenticated category and saved-location metadata endpoints. The typed draft and publish service boundaries already exist; the client does not invent category/location IDs or replace missing backend data with fixtures.

## Release gate

See [`docs/release-checklist.md`](docs/release-checklist.md). A clean mobile build is not sufficient for production: backend authorization, reservation concurrency, replay-safe QR handover, notifications, monitoring, backups, and security tests must pass in staging first.
