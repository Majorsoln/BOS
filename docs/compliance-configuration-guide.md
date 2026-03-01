# BOS Compliance Configuration Guide

> Version: 1.0
> Audience: Administrators configuring tax, regulatory, and compliance rules

---

## 1. Compliance Philosophy

BOS enforces a strict rule: **No hardcoded country or regional logic.**

All compliance behavior is:
- **Admin-configurable** — managed via API
- **Policy-driven** — evaluated at command dispatch
- **Data-defined** — stored as events, never as code branches

```python
# FORBIDDEN — hardcoded regional logic
if country == "TZ":
    vat_rate = Decimal("0.18")

# CORRECT — data-driven configuration
tax_rule = settings.get_tax_rule(business_id, "VAT")
vat_rate = tax_rule.rate
```

---

## 2. Tax Rules

### 2.1 Configuring Tax Rules

Tax rules are configured per business via the System Settings module:

```python
from core.admin.settings import SetTaxRuleRequest

request = SetTaxRuleRequest(
    business_id=business_id,
    tax_code="VAT",
    rate=Decimal("0.18"),
    description="Value Added Tax 18%",
    actor_id="admin-1",
    issued_at=now,
)
```

Event produced: `admin.tax_rule.configured.v1`

### 2.2 Tax Rule Properties

| Field | Type | Description |
|-------|------|-------------|
| `tax_code` | str | Unique code per business (e.g., "VAT", "SDL", "SALES_TAX") |
| `rate` | Decimal | Tax rate as decimal (0.18 = 18%) |
| `description` | str | Human-readable description |

### 2.3 Querying Tax Rules

```python
# Get specific tax rule
rule = settings_projection.get_tax_rule(business_id, "VAT")

# List all tax rules for a business
rules = settings_projection.list_tax_rules(business_id)
```

### 2.4 Overwriting Tax Rules

Tax rules are **last-write-wins** per `(business_id, tax_code)`. Configuring the same tax code again overwrites the previous value. The old value remains in the event history for audit purposes.

---

## 3. Compliance Profiles

### 3.1 Creating a Profile

```bash
POST /v1/admin/compliance-profiles/upsert
{
    "business_id": "...",
    "profile_name": "TZ_STANDARD",
    "rules": {
        "require_efd_receipt": true,
        "require_tin_on_invoice": true,
        "max_cash_transaction": "5000000",
        "require_dual_approval_above": "10000000"
    }
}
```

Event produced: `admin.compliance_profile.upserted.v1`

### 3.2 Profile Schema

Compliance profiles are flexible key-value structures:

| Key Pattern | Type | Example |
|-------------|------|---------|
| `require_*` | boolean | `require_efd_receipt: true` |
| `max_*` | decimal | `max_cash_transaction: 5000000` |
| `min_*` | decimal | `min_invoice_amount: 1000` |
| `enforce_*` | boolean | `enforce_dual_currency: false` |

### 3.3 Deactivating a Profile

```bash
POST /v1/admin/compliance-profiles/deactivate
{
    "business_id": "...",
    "profile_name": "TZ_STANDARD"
}
```

### 3.4 Listing Profiles

```bash
GET /v1/admin/compliance-profiles?business_id=...
```

---

## 4. Regional Configuration Packs

Regional packs bundle country-specific defaults for rapid tenant setup.

### 4.1 Built-In Pack Structure

```python
from core.saas.region_packs import RegisterRegionPackRequest

request = RegisterRegionPackRequest(
    region_code="TZ",
    region_name="Tanzania",
    default_currency="TZS",
    default_timezone="Africa/Dar_es_Salaam",
    date_format="DD/MM/YYYY",
    tax_presets=(
        {"tax_code": "VAT", "rate": "0.18", "description": "Value Added Tax 18%"},
        {"tax_code": "SDL", "rate": "0.045", "description": "Skills Development Levy 4.5%"},
    ),
    compliance_tags=("TRA_EFD", "TIN_REQUIRED"),
    actor_id="platform-admin",
    issued_at=now,
)
```

### 4.2 Applying a Pack

When a region pack is applied to a business, it sets:
- Default tax rules
- Default compliance tags
- Currency and timezone preferences

```python
from core.saas.region_packs import ApplyRegionPackRequest

service.apply_pack(ApplyRegionPackRequest(
    business_id=business_id,
    region_code="TZ",
    actor_id="admin-1",
    issued_at=now,
))
```

### 4.3 Example Region Configurations

**Tanzania (TZ):**
| Setting | Value |
|---------|-------|
| Currency | TZS |
| Timezone | Africa/Dar_es_Salaam |
| VAT | 18% |
| SDL | 4.5% |
| Compliance | TRA EFD, TIN Required |

**Kenya (KE):**
| Setting | Value |
|---------|-------|
| Currency | KES |
| Timezone | Africa/Nairobi |
| VAT | 16% |
| Compliance | KRA eTIMS |

---

## 5. System Properties

General system properties for per-business configuration:

```python
from core.admin.settings import SetSystemPropertyRequest

request = SetSystemPropertyRequest(
    business_id=business_id,
    property_key="audit.retention_days",
    property_value="365",
    actor_id="admin-1",
    issued_at=now,
)
```

### 5.1 Common Properties

| Key | Description | Example Value |
|-----|-------------|---------------|
| `audit.retention_days` | Audit log retention | `365` |
| `rate_limit.max_per_minute` | API rate limit | `60` |
| `session.timeout_minutes` | Session timeout | `30` |
| `currency.default` | Default currency | `TZS` |
| `locale.date_format` | Date display format | `DD/MM/YYYY` |
| `document.default_language` | Document language | `sw` |

---

## 6. Compliance at Command Dispatch

The compliance guard evaluates commands against active compliance profiles:

```
Command arrives
    │
    ▼
Compliance Guard:
  1. Load active compliance profile for business
  2. Check command type against profile rules
  3. If violation → REJECT with COMPLIANCE_VIOLATION code
  4. If pass → continue to next guard
```

### 6.1 Example Enforcement

If `require_dual_approval_above: 10000000` is set and a procurement PO exceeds TZS 10M:
- Command is **REJECTED** with code `COMPLIANCE_VIOLATION`
- Rejection includes `policy_name` for audit

---

## 7. Document Template Compliance

Document templates are admin-managed and comply with regulations:

### 7.1 Template Management

```bash
# Create/update template
POST /v1/admin/document-templates/upsert
{
    "business_id": "...",
    "template_name": "TZ_EFD_RECEIPT",
    "template_type": "receipt",
    "schema": { ... },
    "fields": ["business_name", "tin", "receipt_number", "items", "vat_breakdown"]
}

# Deactivate template
POST /v1/admin/document-templates/deactivate
{
    "business_id": "...",
    "template_name": "TZ_EFD_RECEIPT"
}
```

### 7.2 Template Rules
- Templates are structured JSON (no raw HTML injection)
- Past documents are immutable (once issued, never modified)
- Render must be reproducible (same input → same output)
- PDF and HTML derive from the same snapshot

---

*"Compliance is data-driven, not code-driven. No `if country == X` ever."*
