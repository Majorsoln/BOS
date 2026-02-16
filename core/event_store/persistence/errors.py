"""
BOS Event Store - Persistence Errors
====================================
Deterministic error code and violated rule constants for persistence stage.
"""


class PersistenceRejectionCode:
    """Rejection codes for persistence-stage failures."""

    TRANSACTION_ABORTED = "TRANSACTION_ABORTED"


class PersistenceViolatedRule:
    """Rule identifiers for audit trail during persistence failures."""

    ATOMIC_PERSISTENCE = "ATOMIC_PERSISTENCE"

