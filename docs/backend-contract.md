# FastAPI contract required by the mobile client

All routes are relative to `EXPO_PUBLIC_API_BASE_URL`. JSON APIs are versioned under `/api/v1`. FastAPI OpenAPI is the source of truth; the client validates responses with Zod and maps snake_case DTOs to camelCase domain models.

## Common requirements

- HTTPS outside local development.
- Bearer access tokens; short-lived access token plus rotating refresh token.
- Backend derives identity and roles from the authenticated session, never request body role fields.
- IDs are UUIDs. Timestamps are ISO 8601 with timezone offsets.
- Paginated collections return `items` and `meta` with `page`, `page_size`, `total_items`, and `total_pages`. Standardize notifications to the same shape.
- Failures use the appropriate HTTP status and this envelope:

```json
{
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Safe user-facing message",
    "request_id": "correlation-id",
    "details": {}
  }
}
```

The server returns `x-request-id`; the client sends `X-Client-Request-Id`. Never return stack traces, SQL, internal paths, secrets, private user data, or provider diagnostics.

## Authentication and users

- `POST /api/v1/auth/login/password`
- `POST /api/v1/auth/otp/request`
- `POST /api/v1/auth/otp/verify`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `PUT /api/v1/users/me/location-preference`

Login/verification returns `access_token`, `refresh_token`, and a user with `id`, `display_name`, nullable `email`, nullable `phone_number`, `roles`, nullable `city`, nullable `area`, and `is_verified`. Supported roles are `RECIPIENT`, `FOOD_PROVIDER`, `ORGANIZATION`, `VOLUNTEER`, `ADMIN`, and `SUPER_ADMIN`.

Refresh rotation must revoke replayed/replaced refresh tokens. Logout must revoke the active session. OTP, login, refresh, password-reset, and administrative routes require rate limits.

## Food and discovery

- `GET /api/v1/food` — server-side search with `q`, `city`, `area`, `lat`, `lng`, `radius_km`, `category_id`, `price`, `dietary_type`, `pickup_after`, `pickup_before`, `delivery_available`, `ending_soon`, `page`, and `page_size`.
- `GET /api/v1/food/{id}`
- `GET /api/v1/providers/me/food`
- `POST /api/v1/food` — create a draft using snake_case fields.
- `POST /api/v1/food/{id}/publish`

The server must filter visibility, use PostGIS for proximity, return approximate public distance/location, and reveal exact pickup details only to authorized participants. It owns listing state transitions and expiry.

### Metadata endpoints needed before provider post UI is enabled

The current service can create and publish typed drafts, but a production form cannot safely invent identifiers. Add and document:

- authenticated food-category collection for valid `category_id` choices;
- authenticated provider saved/pickup-location collection for valid `location_id` choices;
- controlled object-storage image upload initiation/completion, including MIME, size, dimensions, and safe filename rules.

Once these OpenAPI contracts exist, implement the eight-step Food, Quantity, Pickup time, Location, Images, Safety, Review, Confirm flow. AI-created drafts must use the same service and always require provider confirmation before publish.

## Reservations and secure handover

- `GET /api/v1/reservations`
- `GET /api/v1/reservations/{id}`
- `POST /api/v1/reservations` with `food_listing_id` and positive integer `quantity`
- `POST /api/v1/reservations/{id}/cancel`
- `POST /api/v1/reservations/{id}/handover-token`
- `POST /api/v1/handovers/confirm` with opaque `token`

The database transaction is authoritative for available quantity. Concurrent requests must lock or atomically update inventory so total reservations never exceed available servings. Every resource lookup enforces ownership/role access to prevent BOLA/IDOR.

Handover tokens are cryptographically random, short-lived, scoped to one reservation, provider-authorized, and one-time use. Confirmation must reject expiry and replay and atomically write the state transition plus audit event.

Reservation states: `PENDING`, `CONFIRMED`, `READY`, `PICKED_UP`, `DELIVERED`, `COMPLETED`, `CANCELLED`, `EXPIRED`, `NO_SHOW`, `DISPUTED`. Responses include server-authorized events with actor, previous/new state, and timestamp.

## Trust and verification

- `POST /api/v1/reports`
- `GET /api/v1/verification-requests/me`
- `POST /api/v1/verification-requests`

Reports support listing or reservation targets and reasons `UNSAFE_FOOD`, `SPOILED_FOOD`, `FAKE_LISTING`, `INCORRECT_QUANTITY`, `NO_SHOW`, `MISLEADING_INFORMATION`, `HARASSMENT_ABUSE`, and `OTHER`. Normal users cannot alter moderation status or audit records. Verification status is set only by authorized backend/admin workflows.

## Volunteer deliveries

- `GET /api/v1/deliveries/available`
- `GET /api/v1/deliveries?status=active|completed`
- `GET /api/v1/deliveries/{id}`
- `POST /api/v1/deliveries/{id}/accept`
- `POST /api/v1/deliveries/{id}/transitions`

Task claim races and state transitions are atomic and server-authorized. Detail responses return `allowed_transitions`; coordinates/addresses are exposed only when assignment and workflow state permit it.

## Notifications

- `GET /api/v1/notifications`
- `POST /api/v1/notifications/{id}/read`
- `POST /api/v1/notifications/devices` with Expo token and native platform

Add device-token replacement and revocation/unregister behavior for sign-out and token rollover. Notification routes must be allowlisted before client navigation. Backend events, not local timers, generate reservation, pickup, expiry, delivery, verification, and report notifications.

## Mano AI

- `POST /api/v1/ai/mano/messages`
- `POST /api/v1/ai/mano/actions/{action_id}/confirm`
- `POST /api/v1/ai/voice/transcriptions` as multipart `audio` plus language

Languages: `en`, `ur`, `ps`, `hno`, `pa`. Native audio is M4A; web audio is WebM. The app sends experience context only for UX; the server re-derives authorization from the session.

The AI layer uses typed tools, never arbitrary SQL. It retrieves current authorized data before making factual claims. Side-effecting proposed actions require explicit confirmation and server-enforced idempotency. Role changes, reservations, quantity, handover, verification, payments, deletion, and admin actions remain deterministic services. Apply per-user rate, input, output, and timeout limits. Marketplace endpoints must remain available when AI is down.

## Backend-owned production guarantees

The mobile client is not a security boundary. FastAPI/PostgreSQL must enforce RBAC, ownership, validation, state machines, transactional quantity, idempotency, rate limiting, audit logs, privacy filtering, account-deletion retention/anonymization, upload controls, and impact derivation from completed events.
