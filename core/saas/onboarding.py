"""
BOS SaaS — Tenant Onboarding Automation
===========================================
Multi-step onboarding workflow for new tenant provisioning.

Steps:
  1. INITIATED — signup request received
  2. BUSINESS_CREATED — tenant created in TenantManager
  3. PLAN_SELECTED — subscription plan chosen
  4. BRANCH_CREATED — initial branch provisioned
  5. ADMIN_SETUP — admin user credentials prepared
  6. COMPLETED — onboarding finished, tenant is operational

All transitions are event-sourced and deterministic.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# ONBOARDING EVENT TYPES
# ══════════════════════════════════════════════════════════════

ONBOARDING_INITIATED_V1 = "saas.onboarding.initiated.v1"
ONBOARDING_STEP_COMPLETED_V1 = "saas.onboarding.step_completed.v1"
ONBOARDING_COMPLETED_V1 = "saas.onboarding.completed.v1"
ONBOARDING_ABANDONED_V1 = "saas.onboarding.abandoned.v1"

ONBOARDING_EVENT_TYPES = (
    ONBOARDING_INITIATED_V1,
    ONBOARDING_STEP_COMPLETED_V1,
    ONBOARDING_COMPLETED_V1,
    ONBOARDING_ABANDONED_V1,
)


# ══════════════════════════════════════════════════════════════
# ONBOARDING STEPS
# ══════════════════════════════════════════════════════════════

class OnboardingStep(Enum):
    INITIATED = "INITIATED"
    BUSINESS_CREATED = "BUSINESS_CREATED"
    PLAN_SELECTED = "PLAN_SELECTED"
    BRANCH_CREATED = "BRANCH_CREATED"
    ADMIN_SETUP = "ADMIN_SETUP"
    COMPLETED = "COMPLETED"


# Ordered step progression
_STEP_ORDER = [
    OnboardingStep.INITIATED,
    OnboardingStep.BUSINESS_CREATED,
    OnboardingStep.PLAN_SELECTED,
    OnboardingStep.BRANCH_CREATED,
    OnboardingStep.ADMIN_SETUP,
    OnboardingStep.COMPLETED,
]

_STEP_INDEX = {step: idx for idx, step in enumerate(_STEP_ORDER)}


class OnboardingStatus(Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


# ══════════════════════════════════════════════════════════════
# ONBOARDING DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class OnboardingRecord:
    """Immutable onboarding flow state."""
    onboarding_id: uuid.UUID
    business_name: str
    country_code: str
    timezone: str
    contact_email: str
    current_step: OnboardingStep
    status: OnboardingStatus
    completed_steps: tuple
    business_id: Optional[uuid.UUID] = None
    plan_id: Optional[uuid.UUID] = None
    branch_id: Optional[uuid.UUID] = None
    initiated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# ONBOARDING REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class InitiateOnboardingRequest:
    business_name: str
    country_code: str
    timezone: str
    contact_email: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class CompleteStepRequest:
    onboarding_id: uuid.UUID
    step: str              # OnboardingStep value
    actor_id: str
    issued_at: datetime
    step_data: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class AbandonOnboardingRequest:
    onboarding_id: uuid.UUID
    actor_id: str
    issued_at: datetime
    reason: str = ""


# ══════════════════════════════════════════════════════════════
# ONBOARDING PROJECTION
# ══════════════════════════════════════════════════════════════

class OnboardingProjection:
    """
    In-memory projection of onboarding flows.

    Rebuilt deterministically from onboarding events.
    """

    projection_name = "onboarding_projection"

    def __init__(self) -> None:
        self._flows: Dict[uuid.UUID, OnboardingRecord] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == ONBOARDING_INITIATED_V1:
            ob_id = uuid.UUID(str(payload["onboarding_id"]))
            self._flows[ob_id] = OnboardingRecord(
                onboarding_id=ob_id,
                business_name=payload["business_name"],
                country_code=payload.get("country_code", ""),
                timezone=payload.get("timezone", "UTC"),
                contact_email=payload.get("contact_email", ""),
                current_step=OnboardingStep.INITIATED,
                status=OnboardingStatus.IN_PROGRESS,
                completed_steps=(OnboardingStep.INITIATED.value,),
                initiated_at=payload.get("issued_at"),
            )

        elif event_type == ONBOARDING_STEP_COMPLETED_V1:
            ob_id = uuid.UUID(str(payload["onboarding_id"]))
            old = self._flows.get(ob_id)
            if old is None:
                return
            step = OnboardingStep(payload["step"])
            step_data = payload.get("step_data", {})

            # Extract IDs from step data
            business_id = old.business_id
            plan_id = old.plan_id
            branch_id = old.branch_id
            if step == OnboardingStep.BUSINESS_CREATED and step_data:
                bid = step_data.get("business_id")
                if bid:
                    business_id = uuid.UUID(str(bid))
            if step == OnboardingStep.PLAN_SELECTED and step_data:
                pid = step_data.get("plan_id")
                if pid:
                    plan_id = uuid.UUID(str(pid))
            if step == OnboardingStep.BRANCH_CREATED and step_data:
                brid = step_data.get("branch_id")
                if brid:
                    branch_id = uuid.UUID(str(brid))

            completed = tuple(list(old.completed_steps) + [step.value])
            self._flows[ob_id] = OnboardingRecord(
                onboarding_id=old.onboarding_id,
                business_name=old.business_name,
                country_code=old.country_code,
                timezone=old.timezone,
                contact_email=old.contact_email,
                current_step=step,
                status=old.status,
                completed_steps=completed,
                business_id=business_id,
                plan_id=plan_id,
                branch_id=branch_id,
                initiated_at=old.initiated_at,
            )

        elif event_type == ONBOARDING_COMPLETED_V1:
            ob_id = uuid.UUID(str(payload["onboarding_id"]))
            old = self._flows.get(ob_id)
            if old is None:
                return
            self._flows[ob_id] = OnboardingRecord(
                onboarding_id=old.onboarding_id,
                business_name=old.business_name,
                country_code=old.country_code,
                timezone=old.timezone,
                contact_email=old.contact_email,
                current_step=OnboardingStep.COMPLETED,
                status=OnboardingStatus.COMPLETED,
                completed_steps=old.completed_steps,
                business_id=old.business_id,
                plan_id=old.plan_id,
                branch_id=old.branch_id,
                initiated_at=old.initiated_at,
                completed_at=payload.get("issued_at"),
            )

        elif event_type == ONBOARDING_ABANDONED_V1:
            ob_id = uuid.UUID(str(payload["onboarding_id"]))
            old = self._flows.get(ob_id)
            if old is None:
                return
            self._flows[ob_id] = OnboardingRecord(
                onboarding_id=old.onboarding_id,
                business_name=old.business_name,
                country_code=old.country_code,
                timezone=old.timezone,
                contact_email=old.contact_email,
                current_step=old.current_step,
                status=OnboardingStatus.ABANDONED,
                completed_steps=old.completed_steps,
                business_id=old.business_id,
                plan_id=old.plan_id,
                branch_id=old.branch_id,
                initiated_at=old.initiated_at,
            )

    def get_flow(self, onboarding_id: uuid.UUID) -> Optional[OnboardingRecord]:
        return self._flows.get(onboarding_id)

    def list_in_progress(self) -> List[OnboardingRecord]:
        return [
            f for f in self._flows.values()
            if f.status == OnboardingStatus.IN_PROGRESS
        ]

    def list_completed(self) -> List[OnboardingRecord]:
        return [
            f for f in self._flows.values()
            if f.status == OnboardingStatus.COMPLETED
        ]

    def truncate(self) -> None:
        self._flows.clear()


# ══════════════════════════════════════════════════════════════
# ONBOARDING SERVICE
# ══════════════════════════════════════════════════════════════

class OnboardingService:
    """
    Orchestrates multi-step tenant onboarding.

    All mutations produce events — no direct state writes.
    """

    def __init__(self, projection: OnboardingProjection) -> None:
        self._projection = projection

    def initiate(
        self, request: InitiateOnboardingRequest
    ) -> Dict[str, Any]:
        """Start a new onboarding flow."""
        ob_id = uuid.uuid4()
        payload = {
            "onboarding_id": str(ob_id),
            "business_name": request.business_name,
            "country_code": request.country_code,
            "timezone": request.timezone,
            "contact_email": request.contact_email,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(ONBOARDING_INITIATED_V1, payload)
        return {
            "onboarding_id": ob_id,
            "events": [{"event_type": ONBOARDING_INITIATED_V1, "payload": payload}],
        }

    def complete_step(
        self, request: CompleteStepRequest
    ) -> Optional[RejectionReason]:
        """Mark an onboarding step as completed."""
        flow = self._projection.get_flow(request.onboarding_id)
        if flow is None:
            return RejectionReason(
                code="ONBOARDING_NOT_FOUND",
                message="Onboarding flow not found.",
                policy_name="complete_step",
            )
        if flow.status != OnboardingStatus.IN_PROGRESS:
            return RejectionReason(
                code="ONBOARDING_NOT_IN_PROGRESS",
                message=f"Onboarding is {flow.status.value}.",
                policy_name="complete_step",
            )

        try:
            step = OnboardingStep(request.step)
        except ValueError:
            return RejectionReason(
                code="INVALID_STEP",
                message=f"Invalid onboarding step: {request.step}.",
                policy_name="complete_step",
            )

        # Must complete steps in order
        current_idx = _STEP_INDEX.get(flow.current_step, 0)
        target_idx = _STEP_INDEX.get(step, 0)
        if target_idx != current_idx + 1:
            return RejectionReason(
                code="STEP_OUT_OF_ORDER",
                message=f"Expected step after {flow.current_step.value}, got {step.value}.",
                policy_name="complete_step",
            )

        payload: Dict[str, Any] = {
            "onboarding_id": str(request.onboarding_id),
            "step": step.value,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        if request.step_data:
            payload["step_data"] = request.step_data

        self._projection.apply(ONBOARDING_STEP_COMPLETED_V1, payload)

        # If final step reached, auto-complete
        if step == OnboardingStep.ADMIN_SETUP:
            complete_payload = {
                "onboarding_id": str(request.onboarding_id),
                "actor_id": request.actor_id,
                "issued_at": request.issued_at,
            }
            self._projection.apply(ONBOARDING_COMPLETED_V1, complete_payload)

        return None

    def abandon(
        self, request: AbandonOnboardingRequest
    ) -> Optional[RejectionReason]:
        flow = self._projection.get_flow(request.onboarding_id)
        if flow is None:
            return RejectionReason(
                code="ONBOARDING_NOT_FOUND",
                message="Onboarding flow not found.",
                policy_name="abandon_onboarding",
            )
        if flow.status != OnboardingStatus.IN_PROGRESS:
            return RejectionReason(
                code="ONBOARDING_NOT_IN_PROGRESS",
                message=f"Onboarding is {flow.status.value}.",
                policy_name="abandon_onboarding",
            )
        self._projection.apply(ONBOARDING_ABANDONED_V1, {
            "onboarding_id": str(request.onboarding_id),
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        })
        return None

    def get_progress(
        self, onboarding_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Return progress summary for an onboarding flow."""
        flow = self._projection.get_flow(onboarding_id)
        if flow is None:
            return None
        total_steps = len(_STEP_ORDER)
        completed_count = len(flow.completed_steps)
        return {
            "onboarding_id": str(flow.onboarding_id),
            "business_name": flow.business_name,
            "status": flow.status.value,
            "current_step": flow.current_step.value,
            "completed_steps": list(flow.completed_steps),
            "total_steps": total_steps,
            "progress_pct": round((completed_count / total_steps) * 100, 1),
            "business_id": str(flow.business_id) if flow.business_id else None,
            "plan_id": str(flow.plan_id) if flow.plan_id else None,
        }
