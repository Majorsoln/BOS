"""
BOS Bootstrap — Self-Check Orchestrator
=========================================
Runs all invariant checks at system startup.
If any check fails → SystemBootstrapError propagates → system refuses to start.

Check order:
1. Event Store table exists
2. Immutability guards active
3. Hash-chain structural integrity
4. Registry sanity
5. Persistence entry point

No auto-fix. No fallback. No silence.
"""

import logging

from core.bootstrap.invariants import (
    check_event_store_table,
    check_hash_chain_integrity,
    check_immutability_guards,
    check_persistence_entry_point,
    check_registry_sanity,
)

logger = logging.getLogger("bos.bootstrap")


def run_bootstrap_checks():
    """
    Execute all system invariant checks.
    Called once at startup via AppConfig.ready().

    If any check raises SystemBootstrapError,
    it propagates and prevents system startup.
    """
    logger.info("═══ BOS Bootstrap Self-Check Starting ═══")

    check_event_store_table()
    check_immutability_guards()
    check_hash_chain_integrity()
    check_registry_sanity()
    check_persistence_entry_point()

    logger.info("═══ BOS Bootstrap Self-Check PASSED ═══")
