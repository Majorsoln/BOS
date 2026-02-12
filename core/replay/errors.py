"""
BOS Replay Engine — Errors
============================
Error types for the replay and projection rebuild layer.
"""


class ReplayError(Exception):
    """Base error for all replay operations."""
    pass


class ReplayChainBrokenError(ReplayError):
    """Hash-chain integrity failed — replay refused."""

    def __init__(self, business_id, detail: str):
        self.business_id = business_id
        self.detail = detail
        super().__init__(
            f"Replay refused — hash-chain broken for business "
            f"{business_id}: {detail}"
        )


class ReplayIsolationError(ReplayError):
    """Attempt to persist an event during replay mode."""

    def __init__(self, message: str = None):
        super().__init__(
            message or "Cannot persist events during replay. "
            "Replay mode is read-only."
        )


class ReplayIntegrityError(ReplayError):
    """Hash recomputation mismatch — event tampered or corrupted."""

    def __init__(self, event_id, expected_hash: str, actual_hash: str):
        self.event_id = event_id
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        super().__init__(
            f"Replay integrity failure — event {event_id}: "
            f"stored hash '{expected_hash}' != "
            f"recomputed hash '{actual_hash}'."
        )
