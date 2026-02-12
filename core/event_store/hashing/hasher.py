"""
BOS Event Store — Hash Computation
====================================
Computes event_hash using SHA-256.

Formula:
    event_hash = SHA256(canonical_json(payload) + previous_event_hash)

Rules:
- Canonical JSON: sorted keys, no whitespace variability
- No salt, no randomness — determinism is mandatory
- First event uses GENESIS_HASH as previous_event_hash
- Same input ALWAYS produces same output

This module ONLY computes. It does not verify, persist, or dispatch.
"""

import hashlib
import json
from typing import Any


# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════

GENESIS_HASH = "GENESIS"


# ══════════════════════════════════════════════════════════════
# CANONICAL SERIALIZATION
# ══════════════════════════════════════════════════════════════

def canonical_serialize(payload: Any) -> str:
    """
    Produce a deterministic JSON string from payload.

    Rules:
    - Keys sorted alphabetically at all levels
    - No whitespace variability (separators=(',', ':'))
    - ensure_ascii=True for cross-platform consistency
    - Default str() for non-serializable types (UUID, datetime)

    Same input ALWAYS produces same output.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


# ══════════════════════════════════════════════════════════════
# HASH COMPUTATION
# ══════════════════════════════════════════════════════════════

def compute_event_hash(payload: Any, previous_event_hash: str) -> str:
    """
    Compute SHA-256 hash for an event.

    Formula:
        event_hash = SHA256(canonical_json(payload) + previous_event_hash)

    Args:
        payload:             Event payload (dict/JSON-serializable).
        previous_event_hash: Hash of the preceding event, or GENESIS_HASH.

    Returns:
        64-character lowercase hex SHA-256 digest.
    """
    canonical = canonical_serialize(payload)
    hash_input = canonical + previous_event_hash
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
