"""
BOS Replay — Models (Django Discovery)
========================================
Re-exports model from checkpoints module for Django migration discovery.
"""

from core.replay.checkpoints import ReplayCheckpoint

__all__ = ["ReplayCheckpoint"]
