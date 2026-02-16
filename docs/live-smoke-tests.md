# BOS Live Smoke Tests (Django Adapter)

This guide validates the thin Django adapter for `core/http_api` handlers.

## Run Server

```bash
python manage.py runserver 127.0.0.1:8000
```

## Seeded Dev Credentials

Configured in `adapters/django_api/wiring.py`:

- `X-API-KEY` admin: `dev-admin-key`
- `X-API-KEY` cashier: `dev-cashier-key`
- `X-BUSINESS-ID`: `11111111-1111-1111-1111-111111111111`
- Admin branch: `22222222-2222-2222-2222-222222222222`
- Cashier branch: `33333333-3333-3333-3333-333333333333`

## Headers

Use:

- `X-API-KEY`
- `X-BUSINESS-ID`
- Optional `X-BRANCH-ID`

## Read Example

```bash
curl -s "http://127.0.0.1:8000/v1/admin/feature-flags?business_id=11111111-1111-1111-1111-111111111111" \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111"
```

## Write Example (set feature flag)

```bash
curl -s -X POST "http://127.0.0.1:8000/v1/admin/feature-flags/set" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111" \
  -d "{\"business_id\":\"11111111-1111-1111-1111-111111111111\",\"flag_key\":\"ENABLE_COMPLIANCE_ENGINE\",\"status\":\"ENABLED\"}"
```

## Negative Scenarios

Missing API key:

```bash
curl -s "http://127.0.0.1:8000/v1/admin/feature-flags?business_id=11111111-1111-1111-1111-111111111111" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111"
```

Expect `ACTOR_REQUIRED_MISSING`.

Invalid API key:

```bash
curl -s "http://127.0.0.1:8000/v1/admin/feature-flags?business_id=11111111-1111-1111-1111-111111111111" \
  -H "X-API-KEY: bad-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111"
```

Expect `ACTOR_INVALID`.

Unauthorized business:

```bash
curl -s "http://127.0.0.1:8000/v1/admin/feature-flags?business_id=99999999-9999-9999-9999-999999999999" \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 99999999-9999-9999-9999-999999999999"
```

Expect `ACTOR_UNAUTHORIZED_BUSINESS`.

Unauthorized branch for cashier:

```bash
curl -s -X POST "http://127.0.0.1:8000/v1/admin/feature-flags/set" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-cashier-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111" \
  -H "X-BRANCH-ID: 22222222-2222-2222-2222-222222222222" \
  -d "{\"business_id\":\"11111111-1111-1111-1111-111111111111\",\"branch_id\":\"22222222-2222-2222-2222-222222222222\",\"flag_key\":\"ENABLE_DOCUMENT_DESIGNER\",\"status\":\"ENABLED\"}"
```

Expect `ACTOR_UNAUTHORIZED_BRANCH`.

Header/body branch mismatch:

```bash
curl -s -X POST "http://127.0.0.1:8000/v1/admin/feature-flags/set" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111" \
  -H "X-BRANCH-ID: 22222222-2222-2222-2222-222222222222" \
  -d "{\"business_id\":\"11111111-1111-1111-1111-111111111111\",\"branch_id\":\"33333333-3333-3333-3333-333333333333\",\"flag_key\":\"ENABLE_DOCUMENT_DESIGNER\",\"status\":\"ENABLED\"}"
```

Expect `INVALID_CONTEXT`.

## Success Path Round Trip

1. Set a flag with admin key.
2. Read `GET /v1/admin/feature-flags`.
3. Confirm the item appears in `data.items`.

