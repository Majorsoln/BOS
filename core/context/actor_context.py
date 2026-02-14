"""
BOS Context - ActorContext
==========================
Immutable actor identity context for command validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ActorContext:
    """
    Canonical actor identity context.

    actor_roles and actor_scopes are optional immutable hints.
    Authorization logic is policy-hook driven, not context-cached.
    """

    actor_type: str
    actor_id: str
    actor_roles: tuple[str, ...] = field(default_factory=tuple)
    actor_scopes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not self.actor_type or not isinstance(self.actor_type, str):
            raise ValueError("actor_type must be a non-empty string.")

        if not self.actor_id or not isinstance(self.actor_id, str):
            raise ValueError("actor_id must be a non-empty string.")

        if not isinstance(self.actor_roles, tuple):
            raise ValueError("actor_roles must be a tuple.")

        if not isinstance(self.actor_scopes, tuple):
            raise ValueError("actor_scopes must be a tuple.")

