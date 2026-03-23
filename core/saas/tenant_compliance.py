"""
BOS SaaS — Tenant Compliance Onboarding
==========================================
Manages per-country compliance policies and tenant compliance profiles.

Country policies define what documents/information a tenant must provide
before they can operate in a given jurisdiction (e.g. business registration
certificate, tax PIN, etc.).

Tenant compliance profiles track the onboarding state for each tenant:
  PENDING → SUBMITTED → APPROVED → ACTIVE
                      → REJECTED (can resubmit)
  ACTIVE → SUSPENDED → REACTIVATED

Compliance profiles are reviewed by platform compliance officers.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════
# EVENT TYPES
# ══════════════════════════════════════════════════════════════

COUNTRY_POLICY_SET_V1 = "saas.compliance.country_policy.set.v1"
COMPLIANCE_PROFILE_SUBMITTED_V1 = "saas.compliance.profile.submitted.v1"
COMPLIANCE_PROFILE_REVIEWED_V1 = "saas.compliance.profile.reviewed.v1"
COMPLIANCE_PROFILE_ACTIVATED_V1 = "saas.compliance.profile.activated.v1"
COMPLIANCE_PROFILE_SUSPENDED_V1 = "saas.compliance.profile.suspended.v1"
COMPLIANCE_PROFILE_REACTIVATED_V1 = "saas.compliance.profile.reactivated.v1"

TENANT_COMPLIANCE_EVENT_TYPES = (
    COUNTRY_POLICY_SET_V1,
    COMPLIANCE_PROFILE_SUBMITTED_V1,
    COMPLIANCE_PROFILE_REVIEWED_V1,
    COMPLIANCE_PROFILE_ACTIVATED_V1,
    COMPLIANCE_PROFILE_SUSPENDED_V1,
    COMPLIANCE_PROFILE_REACTIVATED_V1,
)


# ══════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CountryCompliancePolicy:
    """Defines compliance requirements for a country/jurisdiction."""
    country_code: str               # ISO 3166-1 alpha-2 e.g. "KE"
    display_name: str               # e.g. "Kenya Compliance Policy"
    required_documents: Tuple[str, ...]   # e.g. ("business_registration", "tax_pin", "id_copy")
    required_fields: Tuple[str, ...]      # e.g. ("business_name", "physical_address", "tax_number")
    review_required: bool           # if True, profile must be reviewed before activation
    auto_activate: bool             # if True AND review not required, activate immediately on submit
    updated_at: Optional[datetime] = None
    updated_by: str = ""


@dataclass(frozen=True)
class ReviewDecision:
    """A single review decision on a compliance profile."""
    decision: str       # "approve" or "reject"
    reviewer_id: str
    reason: str
    decided_at: datetime


@dataclass(frozen=True)
class TenantComplianceProfile:
    """
    Tracks a tenant's compliance onboarding state.
    """
    profile_id: str
    business_id: str
    country_code: str
    status: str          # PENDING, SUBMITTED, APPROVED, REJECTED, ACTIVE, SUSPENDED
    submitted_data: Dict[str, Any]   # fields + document references
    submitted_at: Optional[datetime] = None
    submitted_by: str = ""
    decisions: Tuple[ReviewDecision, ...] = ()
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    suspended_reason: str = ""
    reactivated_at: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SetCountryPolicyRequest:
    country_code: str
    display_name: str
    required_documents: Tuple[str, ...]
    required_fields: Tuple[str, ...]
    review_required: bool
    auto_activate: bool
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class SubmitComplianceProfileRequest:
    business_id: str
    country_code: str
    submitted_data: Dict[str, Any]
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class ReviewComplianceProfileRequest:
    profile_id: str
    decision: str       # "approve" or "reject"
    reviewer_id: str
    reason: str
    issued_at: datetime


@dataclass(frozen=True)
class ActivateComplianceProfileRequest:
    profile_id: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class SuspendComplianceProfileRequest:
    profile_id: str
    reason: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class ReactivateComplianceProfileRequest:
    profile_id: str
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# PROJECTION
# ══════════════════════════════════════════════════════════════

class TenantComplianceProjection:
    """In-memory projection of country policies and tenant compliance profiles."""

    projection_name = "tenant_compliance_projection"

    def __init__(self) -> None:
        # country_code → CountryCompliancePolicy
        self._policies: Dict[str, CountryCompliancePolicy] = {}
        # profile_id → TenantComplianceProfile
        self._profiles: Dict[str, TenantComplianceProfile] = {}
        # business_id → profile_id (latest)
        self._business_profiles: Dict[str, str] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == COUNTRY_POLICY_SET_V1:
            self._apply_country_policy(payload)
        elif event_type == COMPLIANCE_PROFILE_SUBMITTED_V1:
            self._apply_submitted(payload)
        elif event_type == COMPLIANCE_PROFILE_REVIEWED_V1:
            self._apply_reviewed(payload)
        elif event_type == COMPLIANCE_PROFILE_ACTIVATED_V1:
            self._apply_activated(payload)
        elif event_type == COMPLIANCE_PROFILE_SUSPENDED_V1:
            self._apply_suspended(payload)
        elif event_type == COMPLIANCE_PROFILE_REACTIVATED_V1:
            self._apply_reactivated(payload)

    def _apply_country_policy(self, payload: Dict[str, Any]) -> None:
        cc = payload["country_code"]
        self._policies[cc] = CountryCompliancePolicy(
            country_code=cc,
            display_name=payload.get("display_name", ""),
            required_documents=tuple(payload.get("required_documents", [])),
            required_fields=tuple(payload.get("required_fields", [])),
            review_required=payload.get("review_required", True),
            auto_activate=payload.get("auto_activate", False),
            updated_at=payload.get("issued_at"),
            updated_by=payload.get("actor_id", ""),
        )

    def _apply_submitted(self, payload: Dict[str, Any]) -> None:
        profile_id = payload["profile_id"]
        business_id = payload["business_id"]
        self._profiles[profile_id] = TenantComplianceProfile(
            profile_id=profile_id,
            business_id=business_id,
            country_code=payload["country_code"],
            status="SUBMITTED",
            submitted_data=payload.get("submitted_data", {}),
            submitted_at=payload.get("issued_at"),
            submitted_by=payload.get("actor_id", ""),
        )
        self._business_profiles[business_id] = profile_id

    def _apply_reviewed(self, payload: Dict[str, Any]) -> None:
        profile_id = payload["profile_id"]
        old = self._profiles.get(profile_id)
        if old is None:
            return
        decision = ReviewDecision(
            decision=payload["decision"],
            reviewer_id=payload["reviewer_id"],
            reason=payload.get("reason", ""),
            decided_at=payload.get("issued_at"),
        )
        new_status = "APPROVED" if payload["decision"] == "approve" else "REJECTED"
        self._profiles[profile_id] = TenantComplianceProfile(
            profile_id=old.profile_id,
            business_id=old.business_id,
            country_code=old.country_code,
            status=new_status,
            submitted_data=old.submitted_data,
            submitted_at=old.submitted_at,
            submitted_by=old.submitted_by,
            decisions=old.decisions + (decision,),
            activated_at=old.activated_at,
            suspended_at=old.suspended_at,
            suspended_reason=old.suspended_reason,
            reactivated_at=old.reactivated_at,
        )

    def _apply_activated(self, payload: Dict[str, Any]) -> None:
        profile_id = payload["profile_id"]
        old = self._profiles.get(profile_id)
        if old is None:
            return
        self._profiles[profile_id] = TenantComplianceProfile(
            profile_id=old.profile_id,
            business_id=old.business_id,
            country_code=old.country_code,
            status="ACTIVE",
            submitted_data=old.submitted_data,
            submitted_at=old.submitted_at,
            submitted_by=old.submitted_by,
            decisions=old.decisions,
            activated_at=payload.get("issued_at"),
            suspended_at=old.suspended_at,
            suspended_reason=old.suspended_reason,
            reactivated_at=old.reactivated_at,
        )

    def _apply_suspended(self, payload: Dict[str, Any]) -> None:
        profile_id = payload["profile_id"]
        old = self._profiles.get(profile_id)
        if old is None:
            return
        self._profiles[profile_id] = TenantComplianceProfile(
            profile_id=old.profile_id,
            business_id=old.business_id,
            country_code=old.country_code,
            status="SUSPENDED",
            submitted_data=old.submitted_data,
            submitted_at=old.submitted_at,
            submitted_by=old.submitted_by,
            decisions=old.decisions,
            activated_at=old.activated_at,
            suspended_at=payload.get("issued_at"),
            suspended_reason=payload.get("reason", ""),
            reactivated_at=old.reactivated_at,
        )

    def _apply_reactivated(self, payload: Dict[str, Any]) -> None:
        profile_id = payload["profile_id"]
        old = self._profiles.get(profile_id)
        if old is None:
            return
        self._profiles[profile_id] = TenantComplianceProfile(
            profile_id=old.profile_id,
            business_id=old.business_id,
            country_code=old.country_code,
            status="ACTIVE",
            submitted_data=old.submitted_data,
            submitted_at=old.submitted_at,
            submitted_by=old.submitted_by,
            decisions=old.decisions,
            activated_at=old.activated_at,
            suspended_at=old.suspended_at,
            suspended_reason=old.suspended_reason,
            reactivated_at=payload.get("issued_at"),
        )

    # ── queries ───────────────────────────────────────────────

    def get_policy(self, country_code: str) -> Optional[CountryCompliancePolicy]:
        return self._policies.get(country_code)

    def list_policies(self) -> List[CountryCompliancePolicy]:
        return list(self._policies.values())

    def get_profile(self, profile_id: str) -> Optional[TenantComplianceProfile]:
        return self._profiles.get(profile_id)

    def get_profile_by_business(self, business_id: str) -> Optional[TenantComplianceProfile]:
        pid = self._business_profiles.get(business_id)
        if pid is None:
            return None
        return self._profiles.get(pid)

    def truncate(self) -> None:
        self._policies.clear()
        self._profiles.clear()
        self._business_profiles.clear()


# ══════════════════════════════════════════════════════════════
# TENANT COMPLIANCE SERVICE
# ══════════════════════════════════════════════════════════════

class TenantComplianceService:
    """
    Manages country compliance policies and tenant compliance profiles.
    """

    def __init__(self, projection: TenantComplianceProjection) -> None:
        self._projection = projection

    def set_country_policy(self, request: SetCountryPolicyRequest) -> Dict[str, Any]:
        """Set or update a country's compliance policy."""
        payload: Dict[str, Any] = {
            "country_code": request.country_code,
            "display_name": request.display_name,
            "required_documents": list(request.required_documents),
            "required_fields": list(request.required_fields),
            "review_required": request.review_required,
            "auto_activate": request.auto_activate,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(COUNTRY_POLICY_SET_V1, payload)
        return {
            "country_code": request.country_code,
            "events": [{"event_type": COUNTRY_POLICY_SET_V1, "payload": payload}],
        }

    def submit_profile(self, request: SubmitComplianceProfileRequest) -> Dict[str, Any]:
        """Submit a tenant compliance profile for review."""
        from core.commands.rejection import RejectionReason

        policy = self._projection.get_policy(request.country_code)
        if policy is None:
            return {
                "rejected": RejectionReason(
                    code="NO_COUNTRY_POLICY",
                    message=f"No compliance policy found for country {request.country_code}.",
                    policy_name="submit_compliance_profile",
                ),
            }

        # Check required fields
        missing_fields = [
            f for f in policy.required_fields
            if f not in request.submitted_data
        ]
        if missing_fields:
            return {
                "rejected": RejectionReason(
                    code="MISSING_REQUIRED_FIELDS",
                    message=f"Missing required fields: {', '.join(missing_fields)}",
                    policy_name="submit_compliance_profile",
                ),
            }

        profile_id = str(uuid.uuid4())
        payload: Dict[str, Any] = {
            "profile_id": profile_id,
            "business_id": request.business_id,
            "country_code": request.country_code,
            "submitted_data": request.submitted_data,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(COMPLIANCE_PROFILE_SUBMITTED_V1, payload)
        return {
            "profile_id": profile_id,
            "status": "SUBMITTED",
            "events": [{"event_type": COMPLIANCE_PROFILE_SUBMITTED_V1, "payload": payload}],
        }

    def review_profile(self, request: ReviewComplianceProfileRequest) -> Dict[str, Any]:
        """Review (approve or reject) a tenant compliance profile."""
        from core.commands.rejection import RejectionReason

        profile = self._projection.get_profile(request.profile_id)
        if profile is None:
            return {
                "rejected": RejectionReason(
                    code="PROFILE_NOT_FOUND",
                    message=f"Compliance profile {request.profile_id} not found.",
                    policy_name="review_compliance_profile",
                ),
            }
        if profile.status not in ("SUBMITTED",):
            return {
                "rejected": RejectionReason(
                    code="INVALID_PROFILE_STATUS",
                    message=f"Profile is in status {profile.status}, expected SUBMITTED.",
                    policy_name="review_compliance_profile",
                ),
            }
        if request.decision not in ("approve", "reject"):
            return {
                "rejected": RejectionReason(
                    code="INVALID_DECISION",
                    message=f"Decision must be 'approve' or 'reject', got '{request.decision}'.",
                    policy_name="review_compliance_profile",
                ),
            }

        payload: Dict[str, Any] = {
            "profile_id": request.profile_id,
            "decision": request.decision,
            "reviewer_id": request.reviewer_id,
            "reason": request.reason,
            "issued_at": request.issued_at,
        }
        self._projection.apply(COMPLIANCE_PROFILE_REVIEWED_V1, payload)
        new_status = "APPROVED" if request.decision == "approve" else "REJECTED"
        return {
            "profile_id": request.profile_id,
            "status": new_status,
            "events": [{"event_type": COMPLIANCE_PROFILE_REVIEWED_V1, "payload": payload}],
        }

    def activate_profile(self, request: ActivateComplianceProfileRequest) -> Dict[str, Any]:
        """Activate an approved compliance profile."""
        from core.commands.rejection import RejectionReason

        profile = self._projection.get_profile(request.profile_id)
        if profile is None:
            return {
                "rejected": RejectionReason(
                    code="PROFILE_NOT_FOUND",
                    message=f"Compliance profile {request.profile_id} not found.",
                    policy_name="activate_compliance_profile",
                ),
            }
        if profile.status not in ("APPROVED",):
            return {
                "rejected": RejectionReason(
                    code="INVALID_PROFILE_STATUS",
                    message=f"Profile is in status {profile.status}, expected APPROVED.",
                    policy_name="activate_compliance_profile",
                ),
            }

        payload: Dict[str, Any] = {
            "profile_id": request.profile_id,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(COMPLIANCE_PROFILE_ACTIVATED_V1, payload)
        return {
            "profile_id": request.profile_id,
            "status": "ACTIVE",
            "events": [{"event_type": COMPLIANCE_PROFILE_ACTIVATED_V1, "payload": payload}],
        }

    def suspend_profile(self, request: SuspendComplianceProfileRequest) -> Dict[str, Any]:
        """Suspend an active compliance profile."""
        from core.commands.rejection import RejectionReason

        profile = self._projection.get_profile(request.profile_id)
        if profile is None:
            return {
                "rejected": RejectionReason(
                    code="PROFILE_NOT_FOUND",
                    message=f"Compliance profile {request.profile_id} not found.",
                    policy_name="suspend_compliance_profile",
                ),
            }
        if profile.status != "ACTIVE":
            return {
                "rejected": RejectionReason(
                    code="INVALID_PROFILE_STATUS",
                    message=f"Profile is in status {profile.status}, expected ACTIVE.",
                    policy_name="suspend_compliance_profile",
                ),
            }

        payload: Dict[str, Any] = {
            "profile_id": request.profile_id,
            "reason": request.reason,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(COMPLIANCE_PROFILE_SUSPENDED_V1, payload)
        return {
            "profile_id": request.profile_id,
            "status": "SUSPENDED",
            "events": [{"event_type": COMPLIANCE_PROFILE_SUSPENDED_V1, "payload": payload}],
        }

    def reactivate_profile(self, request: ReactivateComplianceProfileRequest) -> Dict[str, Any]:
        """Reactivate a suspended compliance profile."""
        from core.commands.rejection import RejectionReason

        profile = self._projection.get_profile(request.profile_id)
        if profile is None:
            return {
                "rejected": RejectionReason(
                    code="PROFILE_NOT_FOUND",
                    message=f"Compliance profile {request.profile_id} not found.",
                    policy_name="reactivate_compliance_profile",
                ),
            }
        if profile.status != "SUSPENDED":
            return {
                "rejected": RejectionReason(
                    code="INVALID_PROFILE_STATUS",
                    message=f"Profile is in status {profile.status}, expected SUSPENDED.",
                    policy_name="reactivate_compliance_profile",
                ),
            }

        payload: Dict[str, Any] = {
            "profile_id": request.profile_id,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(COMPLIANCE_PROFILE_REACTIVATED_V1, payload)
        return {
            "profile_id": request.profile_id,
            "status": "ACTIVE",
            "events": [{"event_type": COMPLIANCE_PROFILE_REACTIVATED_V1, "payload": payload}],
        }
