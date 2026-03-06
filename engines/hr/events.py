"""
BOS HR Engine — Event Type Declarations
========================================
Canonical event types emitted by the HR engine.

Format: engine.domain.action.version
All types must be registered via register_hr_event_types()
before any event of that type can be persisted.
"""

# ── Payroll ────────────────────────────────────────────────────
HR_PAYROLL_RUN_INITIATED_V1 = "hr.payroll.run_initiated.v1"
HR_PAYROLL_RUN_COMPLETED_V1 = "hr.payroll.run_completed.v1"
HR_PAYROLL_RUN_VOIDED_V1 = "hr.payroll.run_voided.v1"

# ── Attendance ────────────────────────────────────────────────
HR_STAFF_CLOCKED_IN_V1 = "hr.staff.clocked_in.v1"
HR_STAFF_CLOCKED_OUT_V1 = "hr.staff.clocked_out.v1"
HR_SHIFT_ASSIGNED_V1 = "hr.shift.assigned.v1"

# ── Staff lifecycle ───────────────────────────────────────────
HR_STAFF_ONBOARDED_V1 = "hr.staff.onboarded.v1"
HR_STAFF_TERMINATED_V1 = "hr.staff.terminated.v1"

HR_EVENT_TYPES = (
    HR_PAYROLL_RUN_INITIATED_V1,
    HR_PAYROLL_RUN_COMPLETED_V1,
    HR_PAYROLL_RUN_VOIDED_V1,
    HR_STAFF_CLOCKED_IN_V1,
    HR_STAFF_CLOCKED_OUT_V1,
    HR_SHIFT_ASSIGNED_V1,
    HR_STAFF_ONBOARDED_V1,
    HR_STAFF_TERMINATED_V1,
)


def register_hr_event_types(event_type_registry) -> None:
    """Register all HR event types with the given EventTypeRegistry."""
    for event_type in sorted(HR_EVENT_TYPES):
        event_type_registry.register(event_type)
