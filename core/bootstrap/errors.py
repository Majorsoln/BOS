"""
BOS Bootstrap — System Errors
===============================
If a core invariant is violated at startup,
the system must refuse to live.
"""


class SystemBootstrapError(Exception):
    """
    Raised when a critical system invariant is violated during boot.

    If this exception is raised:
    - System MUST NOT start
    - No fallback
    - No warning-only mode
    - Error message must be explicit
    """

    def __init__(self, invariant: str, detail: str):
        self.invariant = invariant
        self.detail = detail
        super().__init__(
            f"BOS BOOTSTRAP FAILURE — {invariant}: {detail}"
        )
