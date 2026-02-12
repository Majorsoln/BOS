"""
BOS Replay Engine — Replay Context
=====================================
Thread-local replay isolation flag.

When replay is active:
- is_replay_active() returns True
- persist_event() MUST refuse to write (hard enforcement)
- Subscribers MUST NOT emit new events

This is the single source of truth for replay mode state.
"""

import logging
import threading

logger = logging.getLogger("bos.replay")

_replay_state = threading.local()


def is_replay_active() -> bool:
    """
    Check if replay mode is currently active on this thread.
    Used by persist_event() for hard enforcement.
    """
    return getattr(_replay_state, "active", False)


class ReplayContext:
    """
    Context manager that activates replay isolation mode.

    Usage:
        with ReplayContext():
            # is_replay_active() == True
            # persist_event() will RAISE ReplayIsolationError
    """

    def __enter__(self):
        _replay_state.active = True
        logger.info("Replay mode ACTIVATED — persistence blocked.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _replay_state.active = False
        logger.info("Replay mode DEACTIVATED.")
        return False
