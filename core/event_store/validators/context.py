"""
BOS Event Store — Business Context Protocol
=============================================
This defines the INTERFACE that any BusinessContext must satisfy.
The Event Validator depends on this contract, not on any concrete
implementation.

core/context/ will provide the real implementation.
This file provides the protocol only.

Rules:
- Validator receives context as dependency
- Validator never creates context
- Validator never provides defaults
- If context is missing or invalid → reject
"""

from typing import Optional, Protocol
import uuid


class BusinessContextProtocol(Protocol):
    """
    Structural protocol for business context.
    Any object implementing these methods satisfies the contract.
    No inheritance required — Python structural subtyping.
    """

    def has_active_context(self) -> bool:
        """Return True if a valid business context is currently active."""
        ...

    def get_active_business_id(self) -> Optional[uuid.UUID]:
        """Return the active business_id, or None if no context."""
        ...

    def get_active_branch_id(self) -> Optional[uuid.UUID]:
        """Return the active branch_id, or None if not branch-scoped."""
        ...

    def is_branch_in_business(
        self, branch_id: uuid.UUID, business_id: uuid.UUID
    ) -> bool:
        """
        Return True if branch_id belongs to business_id.
        This is the only ownership check the validator needs.
        """
        ...
