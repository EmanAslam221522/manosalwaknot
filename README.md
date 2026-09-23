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

## Backend contract

See [`docs/backend-contract.md`](docs/backend-contract.md). It lists required endpoints and server-owned guarantees. FastAPI OpenAPI remains the authoritative API specification and should be contract-tested against the Zod DTOs in `services/`.

Provider listing creation remains intentionally unavailable in the UI until the backend supplies authenticated category and saved-location metadata endpoints. The typed draft and publish service boundaries already exist; the client does not invent category/location IDs or replace missing backend data with fixtures.

## Release gate

See [`docs/release-checklist.md`](docs/release-checklist.md). A clean mobile build is not sufficient for production: backend authorization, reservation concurrency, replay-safe QR handover, notifications, monitoring, backups, and security tests must pass in staging first.
