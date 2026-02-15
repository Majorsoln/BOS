"""
BOS Compliance - Rule Schema and Predicate Evaluator
====================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Any


RULE_BLOCK = "BLOCK"
RULE_WARN = "WARN"

OP_EQ = "=="
OP_NE = "!="
OP_IN = "in"
OP_NOT_IN = "not_in"
OP_EXISTS = "exists"
OP_NOT_EXISTS = "not_exists"
OP_GT = "gt"
OP_GTE = "gte"
OP_LT = "lt"
OP_LTE = "lte"

VALID_RULE_SEVERITIES = frozenset({RULE_BLOCK, RULE_WARN})
VALID_OPERATORS = frozenset(
    {
        OP_EQ,
        OP_NE,
        OP_IN,
        OP_NOT_IN,
        OP_EXISTS,
        OP_NOT_EXISTS,
        OP_GT,
        OP_GTE,
        OP_LT,
        OP_LTE,
    }
)


@dataclass(frozen=True)
class ComplianceRule:
    rule_key: str
    applies_to: str
    severity: str
    predicate: dict
    message: str

    def __post_init__(self):
        if not self.rule_key or not isinstance(self.rule_key, str):
            raise ValueError("rule_key must be a non-empty string.")

        if not self.applies_to or not isinstance(self.applies_to, str):
            raise ValueError("applies_to must be a non-empty string.")

        if self.severity not in VALID_RULE_SEVERITIES:
            raise ValueError(
                f"severity '{self.severity}' not valid. "
                f"Must be one of: {sorted(VALID_RULE_SEVERITIES)}"
            )

        if not isinstance(self.predicate, dict):
            raise ValueError("predicate must be a dict.")

        op = self.predicate.get("op")
        if op not in VALID_OPERATORS:
            raise ValueError(
                f"predicate op '{op}' not valid. "
                f"Must be one of: {sorted(VALID_OPERATORS)}"
            )

        if op not in {OP_EXISTS, OP_NOT_EXISTS}:
            if "field" not in self.predicate:
                raise ValueError(
                    "predicate must include 'field' for this operator."
                )
            if "value" not in self.predicate and op not in {
                OP_EXISTS,
                OP_NOT_EXISTS,
            }:
                raise ValueError(
                    "predicate must include 'value' for this operator."
                )

        if not self.message or not isinstance(self.message, str):
            raise ValueError("message must be a non-empty string.")

    def sort_key(self) -> tuple[str, str, str, str, str]:
        normalized_predicate = normalize_predicate(self.predicate)
        return (
            self.rule_key,
            self.severity,
            self.applies_to,
            normalized_predicate,
            self.message,
        )


def normalize_predicate(predicate: dict) -> str:
    return "|".join(
        f"{key}={repr(predicate[key])}" for key in sorted(predicate.keys())
    )


def rule_applies(
    rule: ComplianceRule,
    command,
    targets: tuple[str, ...],
) -> bool:
    applies_to = rule.applies_to

    if applies_to.startswith("COMMAND_TYPE:"):
        pattern = applies_to.split(":", 1)[1]
        return fnmatchcase(command.command_type, pattern)

    return applies_to in targets


def evaluate_rule_predicate(
    rule: ComplianceRule,
    command,
) -> bool:
    predicate = rule.predicate
    op = predicate.get("op")
    field_path = predicate.get("field")
    value = predicate.get("value")

    exists, actual = _resolve_field(command, field_path)

    if op == OP_EXISTS:
        return exists
    if op == OP_NOT_EXISTS:
        return not exists

    if not exists:
        return False

    if op == OP_EQ:
        return actual == value
    if op == OP_NE:
        return actual != value
    if op == OP_IN:
        return actual in value if isinstance(value, (list, tuple, set)) else False
    if op == OP_NOT_IN:
        return (
            actual not in value if isinstance(value, (list, tuple, set)) else False
        )

    try:
        if op == OP_GT:
            return actual > value
        if op == OP_GTE:
            return actual >= value
        if op == OP_LT:
            return actual < value
        if op == OP_LTE:
            return actual <= value
    except TypeError:
        return False

    return False


def _resolve_field(command, field_path: str | None) -> tuple[bool, Any]:
    if not field_path or not isinstance(field_path, str):
        return (False, None)

    path_parts = field_path.split(".")
    if not path_parts:
        return (False, None)

    if path_parts[0] == "command":
        current: Any = command
        path_parts = path_parts[1:]
    else:
        current = command.payload

    if not path_parts:
        return (True, current)

    for part in path_parts:
        if isinstance(current, dict):
            if part not in current:
                return (False, None)
            current = current[part]
        else:
            if not hasattr(current, part):
                return (False, None)
            current = getattr(current, part)

    return (True, current)

