# Free split-stack deployment

This staging/demo deployment uses:

- Render Free for the Docker-based FastAPI service
- Neon Free for PostgreSQL with PostGIS and pgvector
- Upstash Free for Redis-compatible rate limiting

Free services have quotas and availability limits. Render sleeps after 15 minutes without traffic and can take about a minute to wake. Do not treat this topology as production infrastructure.

## 1. Create Neon PostgreSQL

1. Create a free Neon project.
2. Copy both connection strings with TLS enabled:
   - pooled hostname (`-pooler`) for `DATABASE_URL`;
   - direct hostname for `MIGRATIONS_DATABASE_URL`.
3. Keep credentials private. The included Alembic migrations enable `postgis` and `vector`.

The URLs can start with `postgresql://`; the backend normalizes them to the psycopg driver.

## 2. Create Upstash Redis

1. Create one free Redis database.
2. Copy its Redis TCP/TLS URL beginning with `rediss://`.
3. Do not use the REST URL or REST token for `REDIS_URL`.

## 3. Deploy the Render Blueprint

1. In Render, create a new Blueprint from this GitHub repository.
2. Render reads `render.yaml`, builds `backend/Dockerfile`, and selects the Free plan.
3. Supply the prompted private variables:

| Variable                  | Value                                                                                |
| ------------------------- | ------------------------------------------------------------------------------------ |
| `DATABASE_URL`            | Neon pooled TLS URL                                                                  |
| `MIGRATIONS_DATABASE_URL` | Neon direct TLS URL                                                                  |
| `REDIS_URL`               | Upstash `rediss://` URL                                                              |
| `JWT_SECRET`              | Secret of at least 32 characters                                                     |
| `GROQ_API_KEY`            | Backend-only Groq key                                                                |
| `CORS_ORIGINS`            | JSON list of exact published web origins, initially `[]` if the web URL is not known |

Leave `OTP_DEBUG_CODE` unset. `ENVIRONMENT=staging` and the Groq model are defined by the Blueprint.

On the Free plan, the start command runs `alembic upgrade head` before Uvicorn because Render pre-deploy commands and one-off jobs require paid compute. This is acceptable for a one-instance demo service, not a production rollout strategy.

## 4. Verify the API

After Render generates a domain, open:

```text
https://your-service.onrender.com/health
```

Expected dependencies are `ok`. Also verify OpenAPI at `/docs`. If the first request is slow, wait for the free service to wake.

## 5. Wire Expo builds

Set these at build/publish time:

```env
EXPO_PUBLIC_APP_ENV=staging
EXPO_PUBLIC_API_BASE_URL=https://your-service.onrender.com
```

Restart/rebuild after changing Expo public variables; they are embedded into the web and native bundles. Never put database, Redis, JWT, or Groq credentials in an `EXPO_PUBLIC_*` variable.

Once the final web origin exists, update Render `CORS_ORIGINS` to an exact JSON array such as:

```json
["https://your-app.example.com"]
```

Redeploy/restart the API, then test sign-in from that origin.

## Limits and upgrade path

- Render Free sleeps and has monthly usage limits.
- Neon and Upstash free plans have storage/compute/command quotas.
- Free tiers may change; review each provider's current limits before launch.
- For reliable production availability, move migrations to a paid pre-deploy job and use backed-up, monitored services.

Railway remains supported through `backend/railway.json` and `docs/railway-deployment.md`.
