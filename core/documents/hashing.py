"""
BOS Documents - Document Hash
==============================
Computes a deterministic SHA-256 hash over a render_plan.

Doctrine:
- Same render_plan → same hash (deterministic).
- Hash is computed over canonical JSON (sorted keys, no whitespace).
- Used to detect tampering of issued documents.
- Hash is stored in the issuance event and projection.
- This module ONLY computes. It does not persist or dispatch.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical_value(value: Any) -> Any:
    """Recursively normalise a value for canonical JSON serialisation."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _canonical_value(v) for k, v in sorted(value.items())}
    # Coerce anything else to string for determinism
    return str(value)


def canonical_json(value: Any) -> str:
    """
    Produce a canonical (sorted-keys, no-whitespace) JSON string.

    Raises ValueError for values that cannot be serialised.
    """
    normalised = _canonical_value(value)
    return json.dumps(normalised, separators=(",", ":"), ensure_ascii=True)


def compute_render_plan_hash(render_plan: dict) -> str:
    """
    Compute a SHA-256 hex digest over the canonical JSON of render_plan.

    Returns: lowercase hex string, 64 characters.
    """
    if not isinstance(render_plan, dict):
        raise ValueError("render_plan must be a dict.")
    canonical = canonical_json(render_plan)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_render_plan_hash(render_plan: dict, expected_hash: str) -> bool:
    """
    Return True iff compute_render_plan_hash(render_plan) == expected_hash.

    Comparison is constant-time via hmac.compare_digest.
    """
    import hmac
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        return False
    actual = compute_render_plan_hash(render_plan)
    return hmac.compare_digest(actual.lower(), expected_hash.lower())
