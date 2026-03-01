"""
BOS Scope Guard — Pre-execution Scope Enforcement
====================================================
Doctrine: scope-policy.md §4 — Enforcement Rules

Enforces that commands declaring SCOPE_BRANCH_REQUIRED actually
carry a non-None branch_id BEFORE any engine-level processing.

This is a defence-in-depth layer. The event validator also checks
scope at persist time, but early rejection here gives clearer errors
and avoids wasted payload building / event construction.
"""

from __future__ import annotations

from core.commands.base import Command
from core.context.scope import SCOPE_BRANCH_REQUIRED


def enforce_scope_guard(command: Command) -> None:
    """
    Raise ValueError if scope_requirement is BRANCH_REQUIRED but branch_id is None.

    Call this at the TOP of every engine's _execute_command(), before
    feature flag checks, payload building, or event creation.
    """
    if command.scope_requirement == SCOPE_BRANCH_REQUIRED and command.branch_id is None:
        raise ValueError(
            f"Scope violation: command '{command.command_type}' requires "
            f"BRANCH_REQUIRED scope but branch_id is None. "
            f"All branch-scoped operations must specify a branch."
        )
