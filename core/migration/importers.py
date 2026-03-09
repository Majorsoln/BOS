"""
BOS Data Migration — Entity Importers
======================================
Each importer validates and creates entities using existing BOS services.
No direct DB writes — everything goes through the service layer.

Importer signature:
    def import_row(business_id, row, id_mapping_store) -> ImportRowResult
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol

from core.migration.models import (
    EntityType,
    IdMapping,
    ImportRowResult,
    RowStatus,
)

logger = logging.getLogger("bos.migration.importers")


# ══════════════════════════════════════════════════════════════
# ID MAPPING STORE PROTOCOL
# ══════════════════════════════════════════════════════════════

class IdMappingStore(Protocol):
    """Store for external_id → BOS UUID mappings."""

    def get(self, business_id: uuid.UUID, source_system: str,
            entity_type: str, external_id: str) -> Optional[IdMapping]:
        ...

    def put(self, mapping: IdMapping) -> None:
        ...


# ══════════════════════════════════════════════════════════════
# CUSTOMER IMPORTER
# ══════════════════════════════════════════════════════════════

def _validate_customer_row(row: dict) -> Optional[str]:
    """Validate a customer row. Returns error message or None."""
    if not row.get("external_id"):
        return "external_id is required"
    if not row.get("display_name"):
        return "display_name is required"
    return None


def import_customer(
    *,
    business_id: uuid.UUID,
    source_system: str,
    row: dict,
    row_index: int,
    id_store: IdMappingStore,
    create_fn,
) -> ImportRowResult:
    """
    Import a single customer row.

    Expected row format:
        {
            "external_id": "CUST-001",      # required — ID in source ERP
            "display_name": "John Doe",      # required
            "phone": "+254712345678",        # optional
            "email": "john@example.com",     # optional
            "address": "123 Main St",        # optional
        }

    create_fn signature matches identity_store.create_customer_profile:
        create_fn(business_id=..., display_name=..., phone=..., email=..., address=...) -> dict
    """
    external_id = str(row.get("external_id", ""))

    # Validate
    error = _validate_customer_row(row)
    if error:
        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.ERROR.value, error_message=error,
        )

    # Dedup check
    existing = id_store.get(business_id, source_system, EntityType.CUSTOMER.value, external_id)
    if existing:
        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.SKIPPED.value, bos_id=str(existing.bos_id),
            error_message="Already imported",
        )

    # Import
    try:
        result = create_fn(
            business_id=business_id,
            display_name=row["display_name"],
            phone=row.get("phone", ""),
            email=row.get("email", ""),
            address=row.get("address", ""),
        )
        bos_id = uuid.UUID(str(result["customer_id"]))

        id_store.put(IdMapping(
            business_id=business_id, source_system=source_system,
            entity_type=EntityType.CUSTOMER.value, external_id=external_id,
            bos_id=bos_id, imported_at=datetime.now(tz=timezone.utc),
        ))

        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.SUCCESS.value, bos_id=str(bos_id),
        )
    except Exception as e:
        logger.warning("Customer import failed row=%d ext_id=%s: %s", row_index, external_id, e)
        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.ERROR.value, error_message=str(e),
        )


# ══════════════════════════════════════════════════════════════
# SUPPLIER IMPORTER
# ══════════════════════════════════════════════════════════════

def _validate_supplier_row(row: dict) -> Optional[str]:
    if not row.get("external_id"):
        return "external_id is required"
    if not row.get("name"):
        return "name is required"
    return None


def import_supplier(
    *,
    business_id: uuid.UUID,
    source_system: str,
    row: dict,
    row_index: int,
    id_store: IdMappingStore,
    create_fn,
) -> ImportRowResult:
    """
    Import a single supplier row.

    Expected row format:
        {
            "external_id": "SUP-001",
            "name": "ABC Supplies Ltd",
            "contact_person": "Jane",
            "phone": "+254700000000",
            "email": "info@abc.co.ke",
            "address": "Industrial Area",
            "tax_id": "P123456789A",
        }

    create_fn creates a supplier profile in the procurement/identity layer.
    """
    external_id = str(row.get("external_id", ""))

    error = _validate_supplier_row(row)
    if error:
        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.ERROR.value, error_message=error,
        )

    existing = id_store.get(business_id, source_system, EntityType.SUPPLIER.value, external_id)
    if existing:
        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.SKIPPED.value, bos_id=str(existing.bos_id),
            error_message="Already imported",
        )

    try:
        result = create_fn(
            business_id=business_id,
            name=row["name"],
            contact_person=row.get("contact_person", ""),
            phone=row.get("phone", ""),
            email=row.get("email", ""),
            address=row.get("address", ""),
            tax_id=row.get("tax_id", ""),
        )
        bos_id = uuid.UUID(str(result.get("supplier_id", uuid.uuid4())))

        id_store.put(IdMapping(
            business_id=business_id, source_system=source_system,
            entity_type=EntityType.SUPPLIER.value, external_id=external_id,
            bos_id=bos_id, imported_at=datetime.now(tz=timezone.utc),
        ))

        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.SUCCESS.value, bos_id=str(bos_id),
        )
    except Exception as e:
        logger.warning("Supplier import failed row=%d ext_id=%s: %s", row_index, external_id, e)
        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.ERROR.value, error_message=str(e),
        )


# ══════════════════════════════════════════════════════════════
# PRODUCT / INVENTORY ITEM IMPORTER
# ══════════════════════════════════════════════════════════════

def _validate_product_row(row: dict) -> Optional[str]:
    if not row.get("external_id"):
        return "external_id is required"
    if not row.get("name"):
        return "name is required"
    if not row.get("sku"):
        return "sku is required"
    price = row.get("unit_price", 0)
    if not isinstance(price, (int, float)) or price < 0:
        return "unit_price must be a non-negative number"
    return None


def import_product(
    *,
    business_id: uuid.UUID,
    source_system: str,
    row: dict,
    row_index: int,
    id_store: IdMappingStore,
    create_fn,
) -> ImportRowResult:
    """
    Import a single product/inventory item row.

    Expected row format:
        {
            "external_id": "PROD-001",
            "name": "Aluminium Profile 6m",
            "sku": "ALU-6M-001",
            "description": "6 metre aluminium profile",
            "unit_price": 3200,        # minor currency units
            "cost_price": 2800,        # minor currency units (optional)
            "currency": "KES",
            "unit": "PC",              # PC, KG, M, SQM, etc.
            "category": "Raw Material",
            "tax_rate": 0.16,          # VAT rate (optional)
            "opening_qty": 50,         # initial stock quantity (optional)
            "reorder_level": 10,       # min stock alert (optional)
            "barcode": "",             # optional
        }

    create_fn creates a product/item in the inventory layer.
    """
    external_id = str(row.get("external_id", ""))

    error = _validate_product_row(row)
    if error:
        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.ERROR.value, error_message=error,
        )

    existing = id_store.get(business_id, source_system, EntityType.PRODUCT.value, external_id)
    if existing:
        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.SKIPPED.value, bos_id=str(existing.bos_id),
            error_message="Already imported",
        )

    try:
        result = create_fn(
            business_id=business_id,
            name=row["name"],
            sku=row["sku"],
            description=row.get("description", ""),
            unit_price=row.get("unit_price", 0),
            cost_price=row.get("cost_price", 0),
            currency=row.get("currency", "KES"),
            unit=row.get("unit", "PC"),
            category=row.get("category", ""),
            tax_rate=row.get("tax_rate", 0),
            opening_qty=row.get("opening_qty", 0),
            reorder_level=row.get("reorder_level", 0),
            barcode=row.get("barcode", ""),
        )
        bos_id = uuid.UUID(str(result.get("item_id", result.get("product_id", uuid.uuid4()))))

        id_store.put(IdMapping(
            business_id=business_id, source_system=source_system,
            entity_type=EntityType.PRODUCT.value, external_id=external_id,
            bos_id=bos_id, imported_at=datetime.now(tz=timezone.utc),
        ))

        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.SUCCESS.value, bos_id=str(bos_id),
        )
    except Exception as e:
        logger.warning("Product import failed row=%d ext_id=%s: %s", row_index, external_id, e)
        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.ERROR.value, error_message=str(e),
        )


# ══════════════════════════════════════════════════════════════
# OPENING BALANCE IMPORTER
# ══════════════════════════════════════════════════════════════

def _validate_opening_balance_row(row: dict) -> Optional[str]:
    if not row.get("external_id"):
        return "external_id is required"
    if not row.get("account_code"):
        return "account_code is required"
    if "balance" not in row:
        return "balance is required"
    if not isinstance(row["balance"], (int, float)):
        return "balance must be a number"
    return None


def import_opening_balance(
    *,
    business_id: uuid.UUID,
    source_system: str,
    row: dict,
    row_index: int,
    id_store: IdMappingStore,
    post_fn,
) -> ImportRowResult:
    """
    Import a single opening balance row.

    Expected row format:
        {
            "external_id": "OB-001",
            "account_code": "1100",           # BOS chart of accounts code
            "account_name": "Cash at Bank",   # descriptive (optional)
            "balance": 150000,                # minor currency units
            "currency": "KES",
            "as_of_date": "2024-01-01",       # cutover date
            "side": "DEBIT",                  # DEBIT or CREDIT
        }

    post_fn posts an opening balance journal entry to the accounting engine.
    """
    external_id = str(row.get("external_id", ""))

    error = _validate_opening_balance_row(row)
    if error:
        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.ERROR.value, error_message=error,
        )

    existing = id_store.get(business_id, source_system, EntityType.OPENING_BALANCE.value, external_id)
    if existing:
        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.SKIPPED.value, bos_id=str(existing.bos_id),
            error_message="Already imported",
        )

    try:
        result = post_fn(
            business_id=business_id,
            account_code=row["account_code"],
            account_name=row.get("account_name", ""),
            balance=row["balance"],
            currency=row.get("currency", "KES"),
            as_of_date=row.get("as_of_date", ""),
            side=row.get("side", "DEBIT"),
        )
        bos_id = uuid.UUID(str(result.get("journal_id", uuid.uuid4())))

        id_store.put(IdMapping(
            business_id=business_id, source_system=source_system,
            entity_type=EntityType.OPENING_BALANCE.value, external_id=external_id,
            bos_id=bos_id, imported_at=datetime.now(tz=timezone.utc),
        ))

        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.SUCCESS.value, bos_id=str(bos_id),
        )
    except Exception as e:
        logger.warning("Opening balance import failed row=%d ext_id=%s: %s", row_index, external_id, e)
        return ImportRowResult(
            row_index=row_index, external_id=external_id,
            status=RowStatus.ERROR.value, error_message=str(e),
        )


# ══════════════════════════════════════════════════════════════
# IMPORTER REGISTRY
# ══════════════════════════════════════════════════════════════

ENTITY_IMPORTERS = {
    EntityType.CUSTOMER.value: import_customer,
    EntityType.SUPPLIER.value: import_supplier,
    EntityType.PRODUCT.value: import_product,
    EntityType.OPENING_BALANCE.value: import_opening_balance,
}
