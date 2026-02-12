"""
BOS Event Store — Hash-Chain Engine Public API
================================================
"""

from core.event_store.hashing.errors import (
    HashRejectionCode,
    HashViolatedRule,
)
from core.event_store.hashing.hasher import (
    GENESIS_HASH,
    canonical_serialize,
    compute_event_hash,
)
from core.event_store.hashing.verifier import verify_hash_chain

__all__ = [
    "GENESIS_HASH",
    "canonical_serialize",
    "compute_event_hash",
    "verify_hash_chain",
    "HashRejectionCode",
    "HashViolatedRule",
]
