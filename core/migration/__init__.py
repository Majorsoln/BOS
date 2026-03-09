"""
BOS Data Migration Module — "Hamisha Data"
===========================================
Enables businesses migrating from other ERP systems to bulk-import
their existing data into BOS.

Supported entity types:
    CUSTOMER    — Customer profiles (name, phone, email, address)
    PRODUCT     — Inventory items / product catalog
    SUPPLIER    — Supplier contacts for procurement
    OPENING_BAL — Opening balances (accounting)
    TRANSACTION — Historical transaction records (optional)

Architecture:
    1. Admin creates a MigrationJob (specifies source ERP + entity types)
    2. Admin uploads entity data as JSON batches (POST /admin/migration/upload)
    3. MigrationService validates + imports each row:
       - Validation: required fields, data types, uniqueness
       - Dedup: external_id checked against import_log to prevent duplicates
       - Import: entity created via existing BOS services (identity_store, etc.)
    4. Each row produces an ImportResult (success/skip/error + detail)
    5. Job progress tracked via MigrationJobProgress projection

Doctrine:
    - All imports go through standard BOS service layer (no direct DB writes)
    - external_id → BOS UUID mapping stored for cross-reference
    - Idempotent: re-uploading same external_id skips (no duplicates)
    - Tenant-scoped: business_id required on every operation
    - Audit-logged: every import action recorded with actor + timestamp
"""
