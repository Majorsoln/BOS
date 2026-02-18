# BOS Live Smoke Tests - Phase 2.7

Lengo: kuthibitisha `auth`, `permissions`, issuance (`Receipt`, `Quote`, `Invoice`), na persistence ya DB kwa `/v1/docs`.

## 1. Start Server

```bash
python manage.py runserver 127.0.0.1:8000
```

## 2. Prepare Headers (Auth Mode)

Tumia values hizi (au zako):

- `X-API-KEY: dev-admin-key`
- `X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111`
- Optional `X-BRANCH-ID: 22222222-2222-2222-2222-222222222222`

## 3. Auth Smoke

Jaribu read bila `X-API-KEY`:

```bash
curl -s "http://127.0.0.1:8000/v1/docs?business_id=11111111-1111-1111-1111-111111111111"
```

Expected:

- `ok: false`
- `error.code: ACTOR_REQUIRED_MISSING`

## 4. Permission Smoke

Kwa cashier key, jaribu admin-only endpoint:

```bash
curl -s -X POST "http://127.0.0.1:8000/v1/admin/roles/assign" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-cashier-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111" \
  -H "X-BRANCH-ID: 33333333-3333-3333-3333-333333333333" \
  -d "{\"business_id\":\"11111111-1111-1111-1111-111111111111\",\"branch_id\":\"33333333-3333-3333-3333-333333333333\",\"actor_id\":\"smoke-cashier-2\",\"actor_type\":\"HUMAN\",\"role_name\":\"CASHIER\"}"
```

Expected:

- `ok: false`
- `error.code: PERMISSION_DENIED`

## 5. Enable Document Designer Feature

```bash
curl -s -X POST "http://127.0.0.1:8000/v1/admin/feature-flags/set" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111" \
  -d "{\"business_id\":\"11111111-1111-1111-1111-111111111111\",\"flag_key\":\"ENABLE_DOCUMENT_DESIGNER\",\"status\":\"ENABLED\"}"
```

Expected: `ok: true`

## 6. Bootstrap Identity (If Needed)

```bash
curl -s -X POST "http://127.0.0.1:8000/v1/admin/identity/bootstrap" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111" \
  -d "{\"business_id\":\"11111111-1111-1111-1111-111111111111\",\"business_name\":\"BOS Dev Business\",\"default_currency\":\"USD\",\"default_language\":\"en\"}"
```

Expected: `ok: true`

## 7. Issue 3 Documents

### Receipt

```bash
curl -s -X POST "http://127.0.0.1:8000/v1/docs/receipt/issue" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111" \
  -d "{\"business_id\":\"11111111-1111-1111-1111-111111111111\",\"payload\":{\"receipt_no\":\"RCT-2.7-001\",\"issued_at\":\"2026-02-18T10:00:00Z\",\"cashier\":\"Smoke Cashier\",\"line_items\":[{\"name\":\"Item A\",\"quantity\":1,\"unit_price\":10,\"line_total\":10}],\"subtotal\":10,\"tax_total\":1,\"grand_total\":11,\"notes\":\"Smoke receipt\"}}"
```

### Quote

```bash
curl -s -X POST "http://127.0.0.1:8000/v1/docs/quote/issue" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111" \
  -d "{\"business_id\":\"11111111-1111-1111-1111-111111111111\",\"payload\":{\"quote_no\":\"QTE-2.7-001\",\"issued_at\":\"2026-02-18T10:01:00Z\",\"customer_name\":\"Smoke Customer\",\"line_items\":[{\"sku\":\"SKU-1\",\"description\":\"Item A\",\"quantity\":1,\"unit_price\":10}],\"subtotal\":10,\"discount_total\":0,\"grand_total\":10,\"valid_until\":\"2026-02-28\",\"notes\":\"Smoke quote\"}}"
```

### Invoice

```bash
curl -s -X POST "http://127.0.0.1:8000/v1/docs/invoice/issue" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111" \
  -d "{\"business_id\":\"11111111-1111-1111-1111-111111111111\",\"payload\":{\"invoice_no\":\"INV-2.7-001\",\"issued_at\":\"2026-02-18T10:02:00Z\",\"customer_name\":\"Smoke Customer\",\"line_items\":[{\"sku\":\"SKU-1\",\"description\":\"Item A\",\"quantity\":1,\"tax\":1,\"line_total\":11}],\"subtotal\":10,\"tax_total\":1,\"grand_total\":11,\"payment_terms\":\"Due on receipt\",\"notes\":\"Smoke invoice\"}}"
```

Expected kwa zote:

- `ok: true`
- `data.document_id` ipo
- `data.doc_type` sahihi

## 8. Contract Lock Check - GET /v1/docs

```bash
curl -s "http://127.0.0.1:8000/v1/docs?business_id=11111111-1111-1111-1111-111111111111&limit=10" \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111"
```

Hakiki kila item ina fields hizi tu:

- `doc_id`
- `doc_type`
- `status`
- `business_id`
- `branch_id`
- `issued_at`
- `issued_by_actor_id`
- `correlation_id`
- `template_id`
- `template_version`
- `schema_version`
- `totals`
- `links.self`
- `links.render_plan`

Hakiki ordering ni deterministic: `issued_at ASC`, tie-break `doc_id ASC`.

## 9. Cursor Paging Check

Page 1:

```bash
curl -s "http://127.0.0.1:8000/v1/docs?business_id=11111111-1111-1111-1111-111111111111&limit=2" \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111"
```

Chukua `data.next_cursor`, halafu page 2:

```bash
curl -s "http://127.0.0.1:8000/v1/docs?business_id=11111111-1111-1111-1111-111111111111&limit=2&cursor=<PASTE_CURSOR>" \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111"
```

Expected:

- page 2 inaendelea baada ya tuple `(issued_at, doc_id)` ya mwisho ya page 1
- hakuna duplication

## 10. Restart Persistence Proof

1. Stop server.
2. Start server tena:

```bash
python manage.py runserver 127.0.0.1:8000
```

3. Piga tena:

```bash
curl -s "http://127.0.0.1:8000/v1/docs?business_id=11111111-1111-1111-1111-111111111111&limit=10" \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111"
```

Expected:

- docs ulizoissue kabla ya restart bado zipo
- order na contract shape vinafanana na kabla ya restart
