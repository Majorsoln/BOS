"""
BOS Party Primitive — Customer / Vendor / Staff Abstraction
=============================================================
Engine: Core Primitives (Phase 4)
Authority: BOS Doctrine — Deterministic, Event-Sourced

The Party Primitive provides a universal stakeholder abstraction
used by: All engines that deal with external or internal parties.

A "Party" is any entity that participates in business transactions:
- Customer (retail, restaurant, workshop)
- Vendor / Supplier (procurement)
- Staff / Employee (HR, operations)
- Organization (B2B)

RULES (NON-NEGOTIABLE):
- Party definitions are immutable snapshots (versioned)
- Multi-tenant: scoped to business_id
- No PII stored in events — contact details are projections
- Party relationships are explicit (not inferred)
- State derived from events only

This file contains NO persistence logic.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class PartyType(Enum):
    """Classification of party."""
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"
    STAFF = "STAFF"
    ORGANIZATION = "ORGANIZATION"


class PartyStatus(Enum):
    """Party lifecycle status."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    BLOCKED = "BLOCKED"


class ContactType(Enum):
    """Type of contact information."""
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    ADDRESS = "ADDRESS"


# ══════════════════════════════════════════════════════════════
# CONTACT ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ContactEntry:
    """
    A single contact point for a party.
    Contact entries are part of the party snapshot.
    """
    contact_type: ContactType
    value: str
    label: str = ""
    is_primary: bool = False

    def __post_init__(self):
        if not isinstance(self.contact_type, ContactType):
            raise ValueError("contact_type must be ContactType enum.")
        if not self.value or not isinstance(self.value, str):
            raise ValueError("value must be non-empty string.")

    def to_dict(self) -> dict:
        return {
            "contact_type": self.contact_type.value,
            "value": self.value,
            "label": self.label,
            "is_primary": self.is_primary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ContactEntry:
        return cls(
            contact_type=ContactType(data["contact_type"]),
            value=data["value"],
            label=data.get("label", ""),
            is_primary=data.get("is_primary", False),
        )


# ══════════════════════════════════════════════════════════════
# TAX IDENTIFICATION
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TaxIdentification:
    """
    Tax identification for a party (TIN, VAT number, etc.).
    Type and format are data-driven — no country-specific logic.
    """
    tax_id_type: str   # e.g. "TIN", "VAT", "EIN"
    tax_id_value: str

    def __post_init__(self):
        if not self.tax_id_type or not isinstance(self.tax_id_type, str):
            raise ValueError("tax_id_type must be non-empty string.")
        if not self.tax_id_value or not isinstance(self.tax_id_value, str):
            raise ValueError("tax_id_value must be non-empty string.")

    def to_dict(self) -> dict:
        return {
            "tax_id_type": self.tax_id_type,
            "tax_id_value": self.tax_id_value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TaxIdentification:
        return cls(
            tax_id_type=data["tax_id_type"],
            tax_id_value=data["tax_id_value"],
        )


# ══════════════════════════════════════════════════════════════
# PARTY DEFINITION (Immutable Snapshot)
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PartyDefinition:
    """
    Canonical party definition — immutable versioned snapshot.

    Fields:
        party_id:        Unique identifier
        business_id:     Tenant boundary
        party_type:      CUSTOMER | VENDOR | STAFF | ORGANIZATION
        name:            Display name
        code:            Business-assigned code (e.g. "CUST-001")
        version:         Increments on each change
        status:          ACTIVE | INACTIVE | SUSPENDED | BLOCKED
        contacts:        Contact information
        tax_ids:         Tax identification numbers
        tags:            Extensible tags for categorization
        notes:           Free-text notes
    """
    party_id: uuid.UUID
    business_id: uuid.UUID
    party_type: PartyType
    name: str
    code: str
    version: int
    status: PartyStatus = PartyStatus.ACTIVE
    contacts: Tuple[ContactEntry, ...] = ()
    tax_ids: Tuple[TaxIdentification, ...] = ()
    tags: Tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self):
        if not isinstance(self.party_id, uuid.UUID):
            raise ValueError("party_id must be UUID.")
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.party_type, PartyType):
            raise ValueError("party_type must be PartyType enum.")
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be non-empty string.")
        if not self.code or not isinstance(self.code, str):
            raise ValueError("code must be non-empty string.")
        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be positive integer.")
        if not isinstance(self.contacts, tuple):
            raise TypeError("contacts must be a tuple.")
        if not isinstance(self.tax_ids, tuple):
            raise TypeError("tax_ids must be a tuple.")

    def get_primary_contact(
        self, contact_type: ContactType
    ) -> Optional[ContactEntry]:
        """Get the primary contact of a specific type."""
        for c in self.contacts:
            if c.contact_type == contact_type and c.is_primary:
                return c
        # Fallback to first match
        for c in self.contacts:
            if c.contact_type == contact_type:
                return c
        return None

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def to_dict(self) -> dict:
        return {
            "party_id": str(self.party_id),
            "business_id": str(self.business_id),
            "party_type": self.party_type.value,
            "name": self.name,
            "code": self.code,
            "version": self.version,
            "status": self.status.value,
            "contacts": [c.to_dict() for c in self.contacts],
            "tax_ids": [t.to_dict() for t in self.tax_ids],
            "tags": list(self.tags),
            "notes": self.notes,
        }


# ══════════════════════════════════════════════════════════════
# PARTY REGISTRY (In-Memory Projection)
# ══════════════════════════════════════════════════════════════

class PartyRegistry:
    """
    In-memory projection of party definitions.

    Read model — disposable, rebuildable from events.
    Provides lookup by party_id, code, and type filtering.
    """

    def __init__(self, business_id: uuid.UUID):
        self._business_id = business_id
        self._parties: Dict[uuid.UUID, PartyDefinition] = {}
        self._code_index: Dict[str, uuid.UUID] = {}

    @property
    def business_id(self) -> uuid.UUID:
        return self._business_id

    @property
    def party_count(self) -> int:
        return len(self._parties)

    def apply_party(self, party: PartyDefinition) -> None:
        """Register or update a party."""
        if party.business_id != self._business_id:
            raise ValueError(
                f"Tenant isolation violation: party business_id "
                f"{party.business_id} != registry business_id "
                f"{self._business_id}."
            )

        # Check code uniqueness
        existing_id = self._code_index.get(party.code)
        if existing_id is not None and existing_id != party.party_id:
            raise ValueError(
                f"Party code '{party.code}' already assigned to "
                f"party {existing_id}. Code must be unique per business."
            )

        self._parties[party.party_id] = party
        self._code_index[party.code] = party.party_id

    def get_by_id(self, party_id: uuid.UUID) -> Optional[PartyDefinition]:
        return self._parties.get(party_id)

    def get_by_code(self, code: str) -> Optional[PartyDefinition]:
        party_id = self._code_index.get(code)
        if party_id is None:
            return None
        return self._parties.get(party_id)

    def list_by_type(self, party_type: PartyType) -> List[PartyDefinition]:
        return [
            p for p in self._parties.values()
            if p.party_type == party_type
        ]

    def list_active(self) -> List[PartyDefinition]:
        return [
            p for p in self._parties.values()
            if p.status == PartyStatus.ACTIVE
        ]

    def list_by_tag(self, tag: str) -> List[PartyDefinition]:
        return [
            p for p in self._parties.values()
            if p.has_tag(tag)
        ]
