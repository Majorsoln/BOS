# BOS HTTP API Reference

> Version: 1.0
> Base URL: `/v1/`
> Authentication: API Key via `X-API-KEY` header

---

## 1. Authentication

All requests require the following headers:

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-KEY` | Yes | API key for authentication |
| `X-BUSINESS-ID` | Yes | Business tenant UUID |
| `X-BRANCH-ID` | No | Branch UUID (required for branch-scoped operations) |
| `Content-Type` | For POST | `application/json` |

### Example

```bash
curl -s "http://localhost:8000/v1/admin/feature-flags?business_id=..." \
  -H "X-API-KEY: dev-admin-key" \
  -H "X-BUSINESS-ID: 11111111-1111-1111-1111-111111111111"
```

---

## 2. Response Format

### Success Response

```json
{
    "status": "success",
    "data": { ... }
}
```

### Error Response

```json
{
    "status": "error",
    "error": {
        "code": "REASON_CODE",
        "message": "Human-readable description",
        "policy_name": "policy_that_rejected"
    }
}
```

---

## 3. Admin Endpoints

### 3.1 Feature Flags

#### List Feature Flags

```
GET /v1/admin/feature-flags?business_id={uuid}
```

**Response:**
```json
{
    "status": "success",
    "data": {
        "flags": [
            {
                "flag_key": "ENABLE_RETAIL_ENGINE",
                "status": "ENABLED",
                "business_id": "...",
                "branch_id": null
            }
        ]
    }
}
```

#### Set Feature Flag

```
POST /v1/admin/feature-flags/set
```

**Body:**
```json
{
    "business_id": "11111111-1111-1111-1111-111111111111",
    "flag_key": "ENABLE_RETAIL_ENGINE",
    "status": "ENABLED"
}
```

#### Clear Feature Flag

```
POST /v1/admin/feature-flags/clear
```

**Body:**
```json
{
    "business_id": "11111111-1111-1111-1111-111111111111",
    "flag_key": "ENABLE_RETAIL_ENGINE"
}
```

---

### 3.2 Compliance Profiles

#### List Compliance Profiles

```
GET /v1/admin/compliance-profiles?business_id={uuid}
```

#### Upsert Compliance Profile

```
POST /v1/admin/compliance-profiles/upsert
```

**Body:**
```json
{
    "business_id": "...",
    "profile_name": "TZ_STANDARD",
    "rules": {
        "require_efd_receipt": true,
        "require_tin_on_invoice": true
    }
}
```

#### Deactivate Compliance Profile

```
POST /v1/admin/compliance-profiles/deactivate
```

**Body:**
```json
{
    "business_id": "...",
    "profile_name": "TZ_STANDARD"
}
```

---

### 3.3 Document Templates

#### List Document Templates

```
GET /v1/admin/document-templates?business_id={uuid}
```

#### Upsert Document Template

```
POST /v1/admin/document-templates/upsert
```

**Body:**
```json
{
    "business_id": "...",
    "template_name": "TZ_RECEIPT",
    "template_type": "receipt",
    "schema": { ... }
}
```

#### Deactivate Document Template

```
POST /v1/admin/document-templates/deactivate
```

**Body:**
```json
{
    "business_id": "...",
    "template_name": "TZ_RECEIPT"
}
```

---

### 3.4 Identity & Access

#### Bootstrap Identity

First-time setup for a new business:

```
POST /v1/admin/identity/bootstrap
```

**Body:**
```json
{
    "business_id": "...",
    "admin_actor_id": "admin-1",
    "admin_actor_type": "HUMAN"
}
```

#### Assign Role

```
POST /v1/admin/roles/assign
```

**Body:**
```json
{
    "business_id": "...",
    "actor_id": "user-42",
    "role": "cashier"
}
```

#### Revoke Role

```
POST /v1/admin/roles/revoke
```

**Body:**
```json
{
    "business_id": "...",
    "actor_id": "user-42",
    "role": "cashier"
}
```

#### List Roles

```
GET /v1/admin/roles?business_id={uuid}
```

#### List Actors

```
GET /v1/admin/actors?business_id={uuid}
```

---

### 3.5 API Key Management

#### Create API Key

```
POST /v1/admin/api-keys/create
```

**Body:**
```json
{
    "business_id": "...",
    "actor_id": "user-42",
    "label": "POS Terminal 1"
}
```

#### Revoke API Key

```
POST /v1/admin/api-keys/revoke
```

**Body:**
```json
{
    "business_id": "...",
    "key_id": "..."
}
```

#### Rotate API Key

```
POST /v1/admin/api-keys/rotate
```

**Body:**
```json
{
    "business_id": "...",
    "key_id": "..."
}
```

#### List API Keys

```
GET /v1/admin/api-keys?business_id={uuid}
```

---

## 4. Document Issuance Endpoints

### 4.1 Issue Receipt

```
POST /v1/documents/receipts/issue
```

**Body:**
```json
{
    "business_id": "...",
    "branch_id": "...",
    "payload": {
        "customer_name": "John Doe",
        "items": [
            {"name": "Widget", "quantity": 2, "unit_price": "5000.00"}
        ],
        "payment_method": "CASH"
    }
}
```

### 4.2 Issue Quote

```
POST /v1/documents/quotes/issue
```

**Body:**
```json
{
    "business_id": "...",
    "payload": {
        "customer_name": "Acme Corp",
        "items": [
            {"name": "Service Package", "quantity": 1, "unit_price": "150000.00"}
        ],
        "valid_until": "2025-07-01"
    }
}
```

### 4.3 Issue Invoice

```
POST /v1/documents/invoices/issue
```

**Body:**
```json
{
    "business_id": "...",
    "payload": {
        "customer_name": "Acme Corp",
        "items": [
            {"name": "Consulting", "quantity": 10, "unit_price": "50000.00"}
        ],
        "due_date": "2025-07-15",
        "payment_terms": "NET_30"
    }
}
```

---

## 5. Document Rendering Endpoints

### 5.1 Get Render Plan

```
GET /v1/docs/{document_id}/render-plan
```

Returns the structured render plan (JSON) for a document.

### 5.2 Get Rendered HTML

```
GET /v1/docs/{document_id}/render-html
```

Returns rendered HTML for the document.

### 5.3 Get Rendered PDF

```
GET /v1/docs/{document_id}/render-pdf
```

Returns PDF binary for the document.

### 5.4 Verify Document

```
GET /v1/docs/{document_id}/verify
```

Verifies document integrity against the event store hash.

---

## 6. Document Listing

### List Issued Documents

```
GET /v1/admin/documents?business_id={uuid}&limit=50&cursor={cursor}
```

**Query Parameters:**
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `business_id` | Yes | — | Business UUID |
| `branch_id` | No | — | Filter by branch |
| `limit` | No | 50 | Items per page (1-200) |
| `cursor` | No | — | Pagination cursor |

**Response:**
```json
{
    "status": "success",
    "data": {
        "documents": [ ... ],
        "next_cursor": "...",
        "has_more": true
    }
}
```

---

## 7. Error Codes Reference

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `ACTOR_REQUIRED_MISSING` | 401 | No API key or actor provided |
| `PERMISSION_DENIED` | 403 | Role does not allow operation |
| `FEATURE_DISABLED` | 403 | Engine not enabled for business |
| `COMPLIANCE_VIOLATION` | 403 | Violates compliance profile |
| `BUSINESS_SUSPENDED` | 403 | Business is suspended |
| `BUSINESS_CLOSED` | 403 | Business is permanently closed |
| `BRANCH_REQUIRED_MISSING` | 400 | Branch required but not provided |
| `BRANCH_NOT_IN_BUSINESS` | 400 | Branch doesn't belong to business |
| `INVALID_COMMAND_STRUCTURE` | 400 | Request failed validation |
| `DUPLICATE_REQUEST` | 409 | Idempotency check failed |
| `QUOTA_EXCEEDED` | 429 | Plan quota exceeded |
| `AI_EXECUTION_FORBIDDEN` | 403 | AI actor attempted forbidden op |

---

## 8. Dev Credentials (Testing Only)

| Credential | Value |
|------------|-------|
| Admin API Key | `dev-admin-key` |
| Cashier API Key | `dev-cashier-key` |
| Business ID | `11111111-1111-1111-1111-111111111111` |
| Admin Branch | `22222222-2222-2222-2222-222222222222` |
| Cashier Branch | `33333333-3333-3333-3333-333333333333` |

**Warning:** Replace all dev credentials before production deployment.

---

*"Every API contract is a promise. Every response is auditable."*
