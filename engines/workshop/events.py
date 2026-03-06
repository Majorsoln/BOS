"""
BOS Workshop Engine — Event Type Declarations
==============================================
Canonical event types emitted by the workshop engine.

Format: engine.domain.action.version
All types must be registered via register_workshop_event_types()
before any event of that type can be persisted.
"""

# ── Quote lifecycle ────────────────────────────────────────────
WORKSHOP_QUOTE_GENERATED_V1 = "workshop.quote.generated.v1"
WORKSHOP_QUOTE_ACCEPTED_V1 = "workshop.quote.accepted.v1"
WORKSHOP_QUOTE_REJECTED_V1 = "workshop.quote.rejected.v1"
WORKSHOP_QUOTE_EXPIRED_V1 = "workshop.quote.expired.v1"

# ── Project lifecycle ─────────────────────────────────────────
WORKSHOP_PROJECT_STARTED_V1 = "workshop.project.started.v1"
WORKSHOP_PROJECT_COMPLETED_V1 = "workshop.project.completed.v1"
WORKSHOP_PROJECT_ON_HOLD_V1 = "workshop.project.on_hold.v1"

# ── Production ────────────────────────────────────────────────
WORKSHOP_CUTTING_LIST_GENERATED_V1 = "workshop.cutting_list.generated.v1"
WORKSHOP_MATERIAL_COMMITTED_V1 = "workshop.material.committed.v1"

# ── Style management ──────────────────────────────────────────
WORKSHOP_STYLE_CREATED_V1 = "workshop.style.created.v1"
WORKSHOP_STYLE_UPDATED_V1 = "workshop.style.updated.v1"

WORKSHOP_EVENT_TYPES = (
    WORKSHOP_QUOTE_GENERATED_V1,
    WORKSHOP_QUOTE_ACCEPTED_V1,
    WORKSHOP_QUOTE_REJECTED_V1,
    WORKSHOP_QUOTE_EXPIRED_V1,
    WORKSHOP_PROJECT_STARTED_V1,
    WORKSHOP_PROJECT_COMPLETED_V1,
    WORKSHOP_PROJECT_ON_HOLD_V1,
    WORKSHOP_CUTTING_LIST_GENERATED_V1,
    WORKSHOP_MATERIAL_COMMITTED_V1,
    WORKSHOP_STYLE_CREATED_V1,
    WORKSHOP_STYLE_UPDATED_V1,
)


def register_workshop_event_types(event_type_registry) -> None:
    """Register all workshop event types with the given EventTypeRegistry."""
    for event_type in sorted(WORKSHOP_EVENT_TYPES):
        event_type_registry.register(event_type)
