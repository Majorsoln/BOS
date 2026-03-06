"""
BOS Accounting Engine — Event Type Declarations
================================================
Canonical event types emitted by the accounting engine.

Format: engine.domain.action.version
All types must be registered via register_accounting_event_types()
before any event of that type can be persisted.

The accounting engine is append-only: every financial movement is an event.
No direct ledger mutation is ever permitted outside this engine.
"""

# ── Journal entries ────────────────────────────────────────────
ACCOUNTING_JOURNAL_ENTRY_POSTED_V1 = "accounting.journal.entry_posted.v1"
ACCOUNTING_JOURNAL_REVERSAL_POSTED_V1 = "accounting.journal.reversal_posted.v1"

# ── Payroll journals ──────────────────────────────────────────
ACCOUNTING_PAYROLL_JOURNAL_POSTED_V1 = "accounting.payroll.journal_posted.v1"

# ── Revenue ───────────────────────────────────────────────────
ACCOUNTING_REVENUE_RECOGNISED_V1 = "accounting.revenue.recognised.v1"
ACCOUNTING_REVENUE_REVERSED_V1 = "accounting.revenue.reversed.v1"

# ── Obligations ───────────────────────────────────────────────
ACCOUNTING_OBLIGATION_CREATED_V1 = "accounting.obligation.created.v1"
ACCOUNTING_OBLIGATION_SETTLED_V1 = "accounting.obligation.settled.v1"

ACCOUNTING_EVENT_TYPES = (
    ACCOUNTING_JOURNAL_ENTRY_POSTED_V1,
    ACCOUNTING_JOURNAL_REVERSAL_POSTED_V1,
    ACCOUNTING_PAYROLL_JOURNAL_POSTED_V1,
    ACCOUNTING_REVENUE_RECOGNISED_V1,
    ACCOUNTING_REVENUE_REVERSED_V1,
    ACCOUNTING_OBLIGATION_CREATED_V1,
    ACCOUNTING_OBLIGATION_SETTLED_V1,
)


def register_accounting_event_types(event_type_registry) -> None:
    """Register all accounting event types with the given EventTypeRegistry."""
    for event_type in sorted(ACCOUNTING_EVENT_TYPES):
        event_type_registry.register(event_type)
