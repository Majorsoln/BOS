"""
BOS HR Engine — Application Service
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from core.commands.base import Command
from core.feature_flags.evaluator import FeatureFlagEvaluator
from engines.hr.commands import HR_COMMAND_TYPES
from engines.hr.events import (
    resolve_hr_event_type, register_hr_event_types,
    build_employee_onboarded_payload, build_employee_terminated_payload,
    build_shift_started_payload, build_shift_ended_payload,
    build_leave_requested_payload,
)

class EventFactoryProtocol(Protocol):
    def __call__(self, *, command: Command, event_type: str, payload: dict) -> dict: ...

class PersistEventProtocol(Protocol):
    def __call__(self, *, event_data: dict, context: Any, registry: Any, **kw) -> Any: ...


class HRProjectionStore:
    def __init__(self):
        self._events: List[dict] = []
        self._employees: Dict[str, dict] = {}
        self._total_hours: int = 0

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})
        if event_type.startswith("hr.employee.onboarded"):
            self._employees[payload["employee_id"]] = {
                "status": "ACTIVE", "full_name": payload["full_name"],
                "role": payload["role"],
            }
        elif event_type.startswith("hr.employee.terminated"):
            eid = payload["employee_id"]
            if eid in self._employees:
                self._employees[eid]["status"] = "TERMINATED"
        elif event_type.startswith("hr.shift.ended"):
            self._total_hours += payload["hours_worked"]
        elif event_type.startswith("hr.leave.requested"):
            eid = payload["employee_id"]
            if eid in self._employees:
                leaves = self._employees[eid].setdefault("leaves", [])
                leaves.append(payload["leave_id"])

    def get_employee(self, employee_id: str) -> Optional[dict]:
        return self._employees.get(employee_id)

    @property
    def total_hours(self) -> int:
        return self._total_hours

    @property
    def event_count(self) -> int:
        return len(self._events)


PAYLOAD_BUILDERS = {
    "hr.employee.onboard.request": build_employee_onboarded_payload,
    "hr.employee.terminate.request": build_employee_terminated_payload,
    "hr.shift.start.request": build_shift_started_payload,
    "hr.shift.end.request": build_shift_ended_payload,
    "hr.leave.request.request": build_leave_requested_payload,
}


@dataclass(frozen=True)
class HRExecutionResult:
    event_type: str
    event_data: dict
    persist_result: Any
    projection_applied: bool


class _HRCommandHandler:
    def __init__(self, service: "HRService"):
        self._service = service
    def execute(self, command: Command) -> HRExecutionResult:
        return self._service._execute_command(command)


class HRService:
    def __init__(self, *, business_context, command_bus,
                 event_factory: EventFactoryProtocol,
                 persist_event: PersistEventProtocol,
                 event_type_registry,
                 projection_store: HRProjectionStore | None = None,
                 feature_flag_provider=None):
        self._business_context = business_context
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or HRProjectionStore()
        self._feature_flag_provider = feature_flag_provider
        register_hr_event_types(self._event_type_registry)
        handler = _HRCommandHandler(self)
        for ct in sorted(HR_COMMAND_TYPES):
            self._command_bus.register_handler(ct, handler)

    def _is_persist_accepted(self, r: Any) -> bool:
        if hasattr(r, "accepted"):
            return bool(r.accepted)
        if isinstance(r, dict):
            return bool(r.get("accepted"))
        return bool(r)

    def _execute_command(self, command: Command) -> HRExecutionResult:
        ff = FeatureFlagEvaluator.evaluate(command, self._business_context, self._feature_flag_provider)
        if not ff.allowed:
            raise ValueError(f"Feature disabled: {ff.message}")

        event_type = resolve_hr_event_type(command.command_type)
        if event_type is None:
            raise ValueError(f"Unsupported: {command.command_type}")
        builder = PAYLOAD_BUILDERS[command.command_type]
        payload = builder(command)
        event_data = self._event_factory(command=command, event_type=event_type, payload=payload)
        persist_result = self._persist_event(
            event_data=event_data, context=self._business_context,
            registry=self._event_type_registry, scope_requirement=command.scope_requirement)
        applied = False
        if self._is_persist_accepted(persist_result):
            self._projection_store.apply(event_type=event_type, payload=payload)
            applied = True
        return HRExecutionResult(
            event_type=event_type, event_data=event_data,
            persist_result=persist_result, projection_applied=applied)

    @property
    def projection_store(self) -> HRProjectionStore:
        return self._projection_store
