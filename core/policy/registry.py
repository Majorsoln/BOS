"""
BOS Policy Engine — Policy Registry (Stabilization Patch v1.0.2)
==================================================================
Central registry for policy rules with version-scoped snapshots.

Responsibilities:
- Register rule instances
- Enforce unique rule_id + version
- Map rules → applies_to command types
- Domain filtering
- Lock after bootstrap with version snapshot
- Version-scoped rule resolution for replay determinism

Patch v1.0.2:
- Version snapshots: lock() freezes rule set under policy_version
- get_rules_for_command() accepts policy_version for replay
- Unknown version at evaluation time → empty rule set (fail-safe)
- Duplicate rule_id in same version → hard fail at registration

No dynamic imports from engines. All rules registered explicitly.
"""

from __future__ import annotations

import logging
from threading import Lock
from typing import Dict, FrozenSet, List, Optional, Tuple

from core.policy.contracts import BaseRule
from core.policy.exceptions import (
    DuplicateRuleError,
    PolicyVersionNotFound,
    RegistryLockedError,
)

logger = logging.getLogger("bos.policy")


class PolicyRegistry:
    """
    Central registry of all policy rules with version snapshots.

    Thread-safe. Lock-after-bootstrap.

    Usage:
        registry = PolicyRegistry()
        registry.register_rule(NegativeStockBlock())
        registry.register_rule(HighDiscountEscalate())
        registry.lock(version="1.0.0")

        # Query (version-scoped)
        rules = registry.get_rules_for_command(
            "inventory.stock.move.request",
            policy_version="1.0.0",
        )
    """

    def __init__(self):
        self._rules: Dict[str, BaseRule] = {}  # key: "rule_id:version"
        self._command_index: Dict[str, List[BaseRule]] = {}
        self._domain_index: Dict[str, List[BaseRule]] = {}
        self._locked: bool = False
        self._lock = Lock()

        # ── Version snapshots (Fix 3) ─────────────────────────
        # version_id → { command_type → [rules] }
        self._version_snapshots: Dict[
            str, Dict[str, Tuple[BaseRule, ...]]
        ] = {}
        self._locked_versions: FrozenSet[str] = frozenset()

    # ══════════════════════════════════════════════════════════
    # REGISTRATION
    # ══════════════════════════════════════════════════════════

    def register_rule(self, rule: BaseRule) -> None:
        """
        Register a rule instance.

        Validates:
        - Registry not locked
        - Rule is BaseRule subclass
        - rule_id + version is unique (Fix 7)

        Args:
            rule: Instantiated BaseRule subclass.
        """
        if not isinstance(rule, BaseRule):
            raise TypeError(
                f"Expected BaseRule instance, got {type(rule).__name__}."
            )

        key = f"{rule.rule_id}:{rule.version}"

        with self._lock:
            if self._locked:
                raise RegistryLockedError()

            if key in self._rules:
                raise DuplicateRuleError(rule.rule_id, rule.version)

            # ── Store rule ────────────────────────────────────
            self._rules[key] = rule

            # ── Index by command_type ─────────────────────────
            for cmd_type in rule.applies_to:
                if cmd_type not in self._command_index:
                    self._command_index[cmd_type] = []
                self._command_index[cmd_type].append(rule)

            # ── Index by domain ───────────────────────────────
            if rule.domain not in self._domain_index:
                self._domain_index[rule.domain] = []
            self._domain_index[rule.domain].append(rule)

            logger.info(
                f"Rule registered: {rule.rule_id} v{rule.version} "
                f"[{rule.severity}] domain={rule.domain} "
                f"applies_to={rule.applies_to}"
            )

    # ══════════════════════════════════════════════════════════
    # LOCK WITH VERSION SNAPSHOT (Fix 3)
    # ══════════════════════════════════════════════════════════

    def lock(self, version: str = None) -> None:
        """
        Lock registry and freeze version snapshot.

        Args:
            version: Policy version identifier for this snapshot.
                     If None, no snapshot created (backward compat).
        """
        with self._lock:
            if version is not None:
                # ── Freeze snapshot for this version ──────────
                snapshot: Dict[str, Tuple[BaseRule, ...]] = {}
                for cmd_type, rules in self._command_index.items():
                    snapshot[cmd_type] = tuple(
                        sorted(rules, key=lambda r: r.rule_id)
                    )
                self._version_snapshots[version] = snapshot
                self._locked_versions = frozenset(
                    self._version_snapshots.keys()
                )
                logger.info(
                    f"Policy version '{version}' snapshot frozen "
                    f"— {len(self._rules)} rules"
                )

            if not self._locked:
                self._locked = True
                logger.info(
                    f"Policy Registry LOCKED — "
                    f"{len(self._rules)} rules, "
                    f"{len(self._version_snapshots)} version(s)"
                )

    @property
    def is_locked(self) -> bool:
        with self._lock:
            return self._locked

    # ══════════════════════════════════════════════════════════
    # QUERIES (version-scoped)
    # ══════════════════════════════════════════════════════════

    def get_rules_for_command(
        self,
        command_type: str,
        policy_version: str = None,
    ) -> List[BaseRule]:
        """
        Get all rules applicable to a command type.

        If policy_version is provided and a snapshot exists,
        rules are returned from the frozen snapshot (replay-safe).

        If policy_version is unknown, returns empty list (fail-safe).

        Returns rules in deterministic order (sorted by rule_id).
        """
        with self._lock:
            # ── Version-scoped lookup (replay mode) ───────────
            if policy_version is not None:
                snapshot = self._version_snapshots.get(policy_version)
                if snapshot is not None:
                    return list(snapshot.get(command_type, ()))
                # Unknown version → empty (fail-safe, not crash)
                return []

            # ── Latest rules (default) ────────────────────────
            rules = self._command_index.get(command_type, [])
            return sorted(rules, key=lambda r: r.rule_id)

    def has_version(self, version: str) -> bool:
        """Check if a version snapshot exists."""
        with self._lock:
            return version in self._version_snapshots

    def get_locked_versions(self) -> FrozenSet[str]:
        """Return all locked version identifiers."""
        with self._lock:
            return self._locked_versions

    def get_rules_by_domain(self, domain: str) -> List[BaseRule]:
        """Get all rules for a domain, sorted by rule_id."""
        with self._lock:
            rules = self._domain_index.get(domain, [])
            return sorted(rules, key=lambda r: r.rule_id)

    def get_all_rules(self) -> List[BaseRule]:
        """Get all registered rules, sorted by rule_id."""
        with self._lock:
            return sorted(
                self._rules.values(), key=lambda r: r.rule_id
            )

    def get_rule(
        self, rule_id: str, version: str
    ) -> Optional[BaseRule]:
        """Get specific rule by id + version."""
        with self._lock:
            return self._rules.get(f"{rule_id}:{version}")

    def rule_count(self) -> int:
        with self._lock:
            return len(self._rules)
