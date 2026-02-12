"""
BOS Bootstrap — System Self-Defense
=====================================
Ensures BOS never starts in an unsafe state.
"""

from core.bootstrap.errors import SystemBootstrapError
from core.bootstrap.self_check import run_bootstrap_checks

__all__ = [
    "SystemBootstrapError",
    "run_bootstrap_checks",
]
