"""
BOS Context â€” BusinessContext
==============================
Immutable, minimal tenant context for command/event validation.

Notes:
- scope_requirement is command-owned (not stored here).
- is_branch_in_business is a v1 non-security hook.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional

from core.context.actor_context import ActorContext

BranchOwnershipChecker = Callable[[uuid.UUID, uuid.UUID], bool]
ActorBusinessAuthorizationChecker = Callable[
    [ActorContext, uuid.UUID], bool
]
ActorBranchAuthorizationChecker = Callable[
    [ActorContext, uuid.UUID, uuid.UUID], bool
]


@dataclass(frozen=True)
class BusinessContext:
    """
    Canonical business context used by validators.

    business_id is mandatory.
    branch_id is optional (None means business scope).
    """

    business_id: uuid.UUID
    branch_id: Optional[uuid.UUID] = None
    lifecycle_state: str = "ACTIVE"
    active: bool = True
    _branch_ownership_checker: Optional[BranchOwnershipChecker] = field(
        default=None, repr=False, compare=False
    )
    _actor_business_authorization_checker: Optional[
        ActorBusinessAuthorizationChecker
    ] = field(default=None, repr=False, compare=False)
    _actor_branch_authorization_checker: Optional[
        ActorBranchAuthorizationChecker
    ] = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")

        if self.branch_id is not None and not isinstance(
            self.branch_id, uuid.UUID
        ):
            raise ValueError("branch_id must be UUID or None.")

    def has_active_context(self) -> bool:
        return self.active

    def get_active_business_id(self) -> Optional[uuid.UUID]:
        if not self.active:
            return None
        return self.business_id

    def get_active_branch_id(self) -> Optional[uuid.UUID]:
        if not self.active:
            return None
        return self.branch_id

    def is_branch_in_business(
        self, branch_id: uuid.UUID, business_id: uuid.UUID
    ) -> bool:
        """
        v1 non-security hook.
        If no checker is provided, returns True.
        """
        checker = self._branch_ownership_checker
        if checker is None:
            return True
        return bool(checker(branch_id, business_id))

    def get_business_lifecycle_state(self) -> str:
        return self.lifecycle_state

    def is_actor_authorized_for_business(
        self,
        actor_context: ActorContext,
        business_id: uuid.UUID,
    ) -> bool:
        """
        v1 non-security hook.
        If no checker is provided, returns True.
        """
        checker = self._actor_business_authorization_checker
        if checker is None:
            return True
        return bool(checker(actor_context, business_id))

    def is_actor_authorized_for_branch(
        self,
        actor_context: ActorContext,
        business_id: uuid.UUID,
        branch_id: uuid.UUID,
    ) -> bool:
        """
        v1 non-security hook.
        If no checker is provided, returns True.
        """
        checker = self._actor_branch_authorization_checker
        if checker is None:
            return True
        return bool(
            checker(actor_context, business_id, branch_id)
        )
