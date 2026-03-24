"""
BOS SaaS — Tenant Compliance Onboarding
==========================================
State-machine-driven compliance lifecycle for tenant onboarding.

Each tenant must pass through a compliance verification flow before
they can start billing. The flow is governed by per-country policies
that define what documentation and verification steps are required.

State machine:
    draft -> submitted -> under_review -> verified -> active
                       -> rejected -> draft (resubmit)
    active -> restricted -> active | suspended | blocked
    suspended -> active | blocked | deactivated
    blocked -> deactivated
    deactivated -> (terminal)

Immutable audit trail:
    Every state transition produces a ComplianceDecision record
    that captures who did what, when, and why.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from core.commands.rejection import RejectionReason


# ══════════════════════════════════════════════════════════════
# EVENT TYPES
# ══════════════════════════════════════════════════════════════

TENANT_COMPLIANCE_SUBMITTED_V1    = "saas.tenant.compliance.submitted.v1"
TENANT_COMPLIANCE_APPROVED_V1     = "saas.tenant.compliance.approved.v1"
TENANT_COMPLIANCE_REJECTED_V1     = "saas.tenant.compliance.rejected.v1"
TENANT_COMPLIANCE_ACTIVATED_V1    = "saas.tenant.compliance.activated.v1"
TENANT_COMPLIANCE_SUSPENDED_V1    = "saas.tenant.compliance.suspended.v1"
TENANT_COMPLIANCE_REACTIVATED_V1  = "saas.tenant.compliance.reactivated.v1"
TENANT_COMPLIANCE_BLOCKED_V1      = "saas.tenant.compliance.blocked.v1"
TENANT_COMPLIANCE_DEACTIVATED_V1  = "saas.tenant.compliance.deactivated.v1"
COUNTRY_POLICY_SET_V1             = "saas.country_policy.set.v1"

TENANT_COMPLIANCE_EVENT_TYPES = (
    TENANT_COMPLIANCE_SUBMITTED_V1,
    TENANT_COMPLIANCE_APPROVED_V1,
    TENANT_COMPLIANCE_REJECTED_V1,
    TENANT_COMPLIANCE_ACTIVATED_V1,
    TENANT_COMPLIANCE_SUSPENDED_V1,
    TENANT_COMPLIANCE_REACTIVATED_V1,
    TENANT_COMPLIANCE_BLOCKED_V1,
    TENANT_COMPLIANCE_DEACTIVATED_V1,
    COUNTRY_POLICY_SET_V1,
)


# ══════════════════════════════════════════════════════════════
# STATE MACHINE
# ══════════════════════════════════════════════════════════════

VALID_TRANSITIONS: Dict[str, List[str]] = {
    "draft":        ["submitted"],
    "submitted":    ["under_review", "verified", "rejected"],
    "under_review": ["verified", "rejected"],
    "verified":     ["active", "rejected"],
    "active":       ["restricted", "suspended", "blocked", "deactivated"],
    "rejected":     ["draft"],
    "restricted":   ["active", "suspended", "blocked"],
    "suspended":    ["active", "blocked", "deactivated"],
    "blocked":      ["deactivated"],
    "deactivated":  [],
}

VALID_STATES = frozenset(VALID_TRANSITIONS.keys())

VALID_CUSTOMER_TYPES = frozenset({"B2B", "B2C"})

VALID_DECISION_TYPES = frozenset({
    "SUBMITTED", "APPROVED", "REJECTED", "ACTIVATED",
    "SUSPENDED", "REACTIVATED", "BLOCKED", "DEACTIVATED",
})


def _can_transition(current_state: str, target_state: str) -> bool:
    """Check whether a state transition is allowed by the state machine."""
    return target_state in VALID_TRANSITIONS.get(current_state, [])


# ══════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CountryPolicy:
    """
    Per-country compliance requirements.

    Defines what documentation, verification steps, and business model
    restrictions apply to tenants operating in this country.
    """
    country_code: str
    country_name: str
    b2b_allowed: bool
    b2c_allowed: bool
    vat_registration_required: bool
    company_registration_required: bool
    requires_tax_id: bool
    requires_physical_address: bool
    default_trial_days: int = 180
    grace_period_days: int = 30
    manual_review_required: bool = False
    active: bool = True
    version: int = 1


@dataclass(frozen=True)
class TenantComplianceProfile:
    """
    A tenant's compliance state throughout the onboarding lifecycle.

    The ``state`` field tracks the current position in the state machine.
    Verification flags (tax_id_verified, etc.) are set during the review
    step and determine whether the profile can proceed to "active".
    """
    profile_id: str
    business_id: str
    country_code: str
    customer_type: str
    legal_name: str
    trade_name: str = ""
    tax_id: str = ""
    company_registration_number: str = ""
    physical_address: str = ""
    city: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    state: str = "draft"
    tax_id_verified: bool = False
    company_reg_verified: bool = False
    address_verified: bool = False
    eligible_for_billing: bool = False
    rejection_reason: str = ""
    reviewer_id: str = ""
    review_notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    verified_at: Optional[datetime] = None
    pack_ref: str = ""


@dataclass(frozen=True)
class ComplianceDecision:
    """
    Immutable audit record for every compliance state transition.

    Every call to submit, approve, reject, suspend, reactivate, block,
    or deactivate a profile produces exactly one decision record.
    """
    decision_id: str
    profile_id: str
    business_id: str
    decision_type: str
    actor_id: str
    reason: str = ""
    policy_version: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    previous_state: str = ""
    new_state: str = ""


# ══════════════════════════════════════════════════════════════
# REQUEST DTOs
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SubmitComplianceProfileRequest:
    business_id: str
    country_code: str
    customer_type: str
    legal_name: str
    trade_name: str
    tax_id: str
    company_registration_number: str
    physical_address: str
    city: str
    contact_email: str
    contact_phone: str
    actor_id: str
    issued_at: datetime


@dataclass(frozen=True)
class ReviewComplianceProfileRequest:
    profile_id: str
    decision: str          # "approve" or "reject"
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
    actor_id: str
    reason: str
    issued_at: datetime


@dataclass(frozen=True)
class ReactivateComplianceProfileRequest:
    profile_id: str
    actor_id: str
    reason: str
    issued_at: datetime


@dataclass(frozen=True)
class BlockComplianceProfileRequest:
    profile_id: str
    actor_id: str
    reason: str
    issued_at: datetime


@dataclass(frozen=True)
class SetCountryPolicyRequest:
    country_code: str
    country_name: str
    b2b_allowed: bool
    b2c_allowed: bool
    vat_registration_required: bool
    company_registration_required: bool
    requires_tax_id: bool
    requires_physical_address: bool
    default_trial_days: int
    grace_period_days: int
    manual_review_required: bool
    active: bool
    actor_id: str
    issued_at: datetime


# ══════════════════════════════════════════════════════════════
# PROJECTION
# ══════════════════════════════════════════════════════════════

class TenantComplianceProjection:
    """
    In-memory projection of country policies, compliance profiles,
    and audit decisions. Rebuilt deterministically from events.
    """

    projection_name = "tenant_compliance_projection"

    def __init__(self) -> None:
        # country_code -> CountryPolicy
        self._policies: Dict[str, CountryPolicy] = {}
        # profile_id -> TenantComplianceProfile
        self._profiles: Dict[str, TenantComplianceProfile] = {}
        # business_id -> profile_id
        self._profiles_by_business: Dict[str, str] = {}
        # profile_id -> list of ComplianceDecision
        self._decisions: Dict[str, List[ComplianceDecision]] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == COUNTRY_POLICY_SET_V1:
            self._apply_country_policy(payload)
        elif event_type == TENANT_COMPLIANCE_SUBMITTED_V1:
            self._apply_submitted(payload)
        elif event_type == TENANT_COMPLIANCE_APPROVED_V1:
            self._apply_approved(payload)
        elif event_type == TENANT_COMPLIANCE_REJECTED_V1:
            self._apply_rejected(payload)
        elif event_type == TENANT_COMPLIANCE_ACTIVATED_V1:
            self._apply_activated(payload)
        elif event_type == TENANT_COMPLIANCE_SUSPENDED_V1:
            self._apply_suspended(payload)
        elif event_type == TENANT_COMPLIANCE_REACTIVATED_V1:
            self._apply_reactivated(payload)
        elif event_type == TENANT_COMPLIANCE_BLOCKED_V1:
            self._apply_blocked(payload)
        elif event_type == TENANT_COMPLIANCE_DEACTIVATED_V1:
            self._apply_deactivated(payload)

    # -- country policy ------------------------------------------

    def _apply_country_policy(self, payload: Dict[str, Any]) -> None:
        country_code = payload["country_code"]
        existing = self._policies.get(country_code)
        new_version = (existing.version + 1) if existing else 1

        self._policies[country_code] = CountryPolicy(
            country_code=country_code,
            country_name=payload.get("country_name", ""),
            b2b_allowed=payload.get("b2b_allowed", True),
            b2c_allowed=payload.get("b2c_allowed", True),
            vat_registration_required=payload.get("vat_registration_required", False),
            company_registration_required=payload.get("company_registration_required", False),
            requires_tax_id=payload.get("requires_tax_id", False),
            requires_physical_address=payload.get("requires_physical_address", False),
            default_trial_days=payload.get("default_trial_days", 180),
            grace_period_days=payload.get("grace_period_days", 30),
            manual_review_required=payload.get("manual_review_required", False),
            active=payload.get("active", True),
            version=new_version,
        )

    # -- profile lifecycle ---------------------------------------

    def _apply_submitted(self, payload: Dict[str, Any]) -> None:
        profile_id = payload["profile_id"]
        business_id = payload["business_id"]
        state = payload.get("state", "submitted")
        now = payload.get("issued_at", datetime.utcnow())

        profile = TenantComplianceProfile(
            profile_id=profile_id,
            business_id=business_id,
            country_code=payload.get("country_code", ""),
            customer_type=payload.get("customer_type", "B2C"),
            legal_name=payload.get("legal_name", ""),
            trade_name=payload.get("trade_name", ""),
            tax_id=payload.get("tax_id", ""),
            company_registration_number=payload.get("company_registration_number", ""),
            physical_address=payload.get("physical_address", ""),
            city=payload.get("city", ""),
            contact_email=payload.get("contact_email", ""),
            contact_phone=payload.get("contact_phone", ""),
            state=state,
            pack_ref=payload.get("pack_ref", ""),
            created_at=now,
            updated_at=now,
        )
        self._profiles[profile_id] = profile
        self._profiles_by_business[business_id] = profile_id

        decision = ComplianceDecision(
            decision_id=payload.get("decision_id", str(uuid.uuid4())),
            profile_id=profile_id,
            business_id=business_id,
            decision_type="SUBMITTED",
            actor_id=payload.get("actor_id", ""),
            reason=payload.get("reason", ""),
            policy_version=payload.get("policy_version", 0),
            timestamp=now,
            previous_state="draft",
            new_state=state,
        )
        self._decisions.setdefault(profile_id, []).append(decision)

    def _apply_approved(self, payload: Dict[str, Any]) -> None:
        profile_id = payload["profile_id"]
        old = self._profiles.get(profile_id)
        if old is None:
            return
        now = payload.get("issued_at", datetime.utcnow())

        self._profiles[profile_id] = TenantComplianceProfile(
            profile_id=old.profile_id,
            business_id=old.business_id,
            country_code=old.country_code,
            customer_type=old.customer_type,
            legal_name=old.legal_name,
            trade_name=old.trade_name,
            tax_id=old.tax_id,
            company_registration_number=old.company_registration_number,
            physical_address=old.physical_address,
            city=old.city,
            contact_email=old.contact_email,
            contact_phone=old.contact_phone,
            state="verified",
            tax_id_verified=payload.get("tax_id_verified", True),
            company_reg_verified=payload.get("company_reg_verified", True),
            address_verified=payload.get("address_verified", True),
            eligible_for_billing=old.eligible_for_billing,
            rejection_reason="",
            reviewer_id=payload.get("reviewer_id", ""),
            review_notes=payload.get("reason", ""),
            created_at=old.created_at,
            updated_at=now,
            verified_at=now,
            pack_ref=old.pack_ref,
        )

        decision = ComplianceDecision(
            decision_id=payload.get("decision_id", str(uuid.uuid4())),
            profile_id=profile_id,
            business_id=old.business_id,
            decision_type="APPROVED",
            actor_id=payload.get("reviewer_id", ""),
            reason=payload.get("reason", ""),
            policy_version=payload.get("policy_version", 0),
            timestamp=now,
            previous_state=old.state,
            new_state="verified",
        )
        self._decisions.setdefault(profile_id, []).append(decision)

    def _apply_rejected(self, payload: Dict[str, Any]) -> None:
        profile_id = payload["profile_id"]
        old = self._profiles.get(profile_id)
        if old is None:
            return
        now = payload.get("issued_at", datetime.utcnow())

        self._profiles[profile_id] = TenantComplianceProfile(
            profile_id=old.profile_id,
            business_id=old.business_id,
            country_code=old.country_code,
            customer_type=old.customer_type,
            legal_name=old.legal_name,
            trade_name=old.trade_name,
            tax_id=old.tax_id,
            company_registration_number=old.company_registration_number,
            physical_address=old.physical_address,
            city=old.city,
            contact_email=old.contact_email,
            contact_phone=old.contact_phone,
            state="rejected",
            tax_id_verified=old.tax_id_verified,
            company_reg_verified=old.company_reg_verified,
            address_verified=old.address_verified,
            eligible_for_billing=False,
            rejection_reason=payload.get("reason", ""),
            reviewer_id=payload.get("reviewer_id", ""),
            review_notes=payload.get("reason", ""),
            created_at=old.created_at,
            updated_at=now,
            verified_at=old.verified_at,
            pack_ref=old.pack_ref,
        )

        decision = ComplianceDecision(
            decision_id=payload.get("decision_id", str(uuid.uuid4())),
            profile_id=profile_id,
            business_id=old.business_id,
            decision_type="REJECTED",
            actor_id=payload.get("reviewer_id", ""),
            reason=payload.get("reason", ""),
            policy_version=payload.get("policy_version", 0),
            timestamp=now,
            previous_state=old.state,
            new_state="rejected",
        )
        self._decisions.setdefault(profile_id, []).append(decision)

    def _apply_state_change(
        self,
        payload: Dict[str, Any],
        new_state: str,
        decision_type: str,
        *,
        eligible_for_billing: Optional[bool] = None,
    ) -> None:
        """Generic helper for simple state transitions (activate, suspend, etc.)."""
        profile_id = payload["profile_id"]
        old = self._profiles.get(profile_id)
        if old is None:
            return
        now = payload.get("issued_at", datetime.utcnow())
        billing = eligible_for_billing if eligible_for_billing is not None else old.eligible_for_billing

        self._profiles[profile_id] = TenantComplianceProfile(
            profile_id=old.profile_id,
            business_id=old.business_id,
            country_code=old.country_code,
            customer_type=old.customer_type,
            legal_name=old.legal_name,
            trade_name=old.trade_name,
            tax_id=old.tax_id,
            company_registration_number=old.company_registration_number,
            physical_address=old.physical_address,
            city=old.city,
            contact_email=old.contact_email,
            contact_phone=old.contact_phone,
            state=new_state,
            tax_id_verified=old.tax_id_verified,
            company_reg_verified=old.company_reg_verified,
            address_verified=old.address_verified,
            eligible_for_billing=billing,
            rejection_reason=old.rejection_reason,
            reviewer_id=old.reviewer_id,
            review_notes=old.review_notes,
            created_at=old.created_at,
            updated_at=now,
            verified_at=old.verified_at,
            pack_ref=old.pack_ref,
        )

        decision = ComplianceDecision(
            decision_id=payload.get("decision_id", str(uuid.uuid4())),
            profile_id=profile_id,
            business_id=old.business_id,
            decision_type=decision_type,
            actor_id=payload.get("actor_id", ""),
            reason=payload.get("reason", ""),
            policy_version=payload.get("policy_version", 0),
            timestamp=now,
            previous_state=old.state,
            new_state=new_state,
        )
        self._decisions.setdefault(profile_id, []).append(decision)

    def _apply_activated(self, payload: Dict[str, Any]) -> None:
        self._apply_state_change(payload, "active", "ACTIVATED", eligible_for_billing=True)

    def _apply_suspended(self, payload: Dict[str, Any]) -> None:
        self._apply_state_change(payload, "suspended", "SUSPENDED", eligible_for_billing=False)

    def _apply_reactivated(self, payload: Dict[str, Any]) -> None:
        self._apply_state_change(payload, "active", "REACTIVATED", eligible_for_billing=True)

    def _apply_blocked(self, payload: Dict[str, Any]) -> None:
        self._apply_state_change(payload, "blocked", "BLOCKED", eligible_for_billing=False)

    def _apply_deactivated(self, payload: Dict[str, Any]) -> None:
        self._apply_state_change(payload, "deactivated", "DEACTIVATED", eligible_for_billing=False)

    # -- queries -------------------------------------------------

    def get_policy(self, country_code: str) -> Optional[CountryPolicy]:
        """Return the country policy for the given country code, or None."""
        return self._policies.get(country_code)

    def list_policies(self) -> List[CountryPolicy]:
        """Return all registered country policies."""
        return list(self._policies.values())

    def get_profile(self, profile_id: str) -> Optional[TenantComplianceProfile]:
        """Return a compliance profile by its ID."""
        return self._profiles.get(profile_id)

    def get_profile_by_business(self, business_id: str) -> Optional[TenantComplianceProfile]:
        """Return the compliance profile for a business, or None."""
        profile_id = self._profiles_by_business.get(business_id)
        if profile_id is None:
            return None
        return self._profiles.get(profile_id)

    def get_decisions(self, profile_id: str) -> List[ComplianceDecision]:
        """Return all compliance decisions for a profile, in chronological order."""
        return list(self._decisions.get(profile_id, []))

    def truncate(self) -> None:
        """Clear all projection state. Used in tests."""
        self._policies.clear()
        self._profiles.clear()
        self._profiles_by_business.clear()
        self._decisions.clear()


# ══════════════════════════════════════════════════════════════
# TENANT COMPLIANCE SERVICE
# ══════════════════════════════════════════════════════════════

class TenantComplianceService:
    """
    Manages tenant compliance onboarding lifecycle.

    Enforces the state machine, validates against country policies,
    and produces immutable audit decisions for every transition.
    """

    def __init__(self, projection: TenantComplianceProjection) -> None:
        self._projection = projection

    # -- country policy ------------------------------------------

    def set_country_policy(
        self, request: SetCountryPolicyRequest
    ) -> Dict[str, Any]:
        """
        Create or update a country policy.
        Version is auto-incremented on each update.
        """
        payload: Dict[str, Any] = {
            "country_code": request.country_code,
            "country_name": request.country_name,
            "b2b_allowed": request.b2b_allowed,
            "b2c_allowed": request.b2c_allowed,
            "vat_registration_required": request.vat_registration_required,
            "company_registration_required": request.company_registration_required,
            "requires_tax_id": request.requires_tax_id,
            "requires_physical_address": request.requires_physical_address,
            "default_trial_days": request.default_trial_days,
            "grace_period_days": request.grace_period_days,
            "manual_review_required": request.manual_review_required,
            "active": request.active,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
        }
        self._projection.apply(COUNTRY_POLICY_SET_V1, payload)

        policy = self._projection.get_policy(request.country_code)
        return {
            "country_code": request.country_code,
            "version": policy.version if policy else 1,
            "events": [{"event_type": COUNTRY_POLICY_SET_V1, "payload": payload}],
        }

    # -- submit --------------------------------------------------

    def submit_compliance_profile(
        self, request: SubmitComplianceProfileRequest
    ) -> Union[Dict[str, Any], RejectionReason]:
        """
        Submit a new compliance profile for a business.

        Validates:
        - Country policy exists and is active.
        - Customer type (B2B/B2C) is allowed by the country policy.
        - Required fields are present (tax_id, address, etc.).
        - Business does not already have a non-rejected profile.

        On success, profile enters "submitted" (or "under_review" if
        the country policy requires manual review).
        """
        policy = self._projection.get_policy(request.country_code)
        if policy is None:
            return RejectionReason(
                code="COUNTRY_POLICY_NOT_FOUND",
                message=f"No compliance policy found for country '{request.country_code}'.",
                policy_name="submit_compliance_profile",
            )

        if not policy.active:
            return RejectionReason(
                code="COUNTRY_POLICY_INACTIVE",
                message=f"Country policy for '{request.country_code}' is inactive.",
                policy_name="submit_compliance_profile",
            )

        # Validate customer type against country policy
        if request.customer_type not in VALID_CUSTOMER_TYPES:
            return RejectionReason(
                code="INVALID_CUSTOMER_TYPE",
                message=f"Customer type must be one of: {', '.join(sorted(VALID_CUSTOMER_TYPES))}.",
                policy_name="submit_compliance_profile",
            )

        if request.customer_type == "B2B" and not policy.b2b_allowed:
            return RejectionReason(
                code="B2B_NOT_ALLOWED",
                message=f"B2B is not allowed in country '{request.country_code}'.",
                policy_name="submit_compliance_profile",
            )

        if request.customer_type == "B2C" and not policy.b2c_allowed:
            return RejectionReason(
                code="B2C_NOT_ALLOWED",
                message=f"B2C is not allowed in country '{request.country_code}'.",
                policy_name="submit_compliance_profile",
            )

        # Validate required fields based on country policy
        if policy.requires_tax_id and not request.tax_id.strip():
            return RejectionReason(
                code="TAX_ID_REQUIRED",
                message=f"Tax ID is required for country '{request.country_code}'.",
                policy_name="submit_compliance_profile",
            )

        if policy.company_registration_required and not request.company_registration_number.strip():
            return RejectionReason(
                code="COMPANY_REGISTRATION_REQUIRED",
                message=f"Company registration number is required for country '{request.country_code}'.",
                policy_name="submit_compliance_profile",
            )

        if policy.requires_physical_address and not request.physical_address.strip():
            return RejectionReason(
                code="PHYSICAL_ADDRESS_REQUIRED",
                message=f"Physical address is required for country '{request.country_code}'.",
                policy_name="submit_compliance_profile",
            )

        # Check for existing non-rejected profile
        existing = self._projection.get_profile_by_business(request.business_id)
        if existing is not None and existing.state != "rejected":
            return RejectionReason(
                code="PROFILE_ALREADY_EXISTS",
                message=(
                    f"Business '{request.business_id}' already has a compliance profile "
                    f"in state '{existing.state}'."
                ),
                policy_name="submit_compliance_profile",
            )

        # Determine initial state
        initial_state = "under_review" if policy.manual_review_required else "submitted"

        profile_id = str(uuid.uuid4())
        decision_id = str(uuid.uuid4())

        payload: Dict[str, Any] = {
            "profile_id": profile_id,
            "business_id": request.business_id,
            "country_code": request.country_code,
            "customer_type": request.customer_type,
            "legal_name": request.legal_name,
            "trade_name": request.trade_name,
            "tax_id": request.tax_id,
            "company_registration_number": request.company_registration_number,
            "physical_address": request.physical_address,
            "city": request.city,
            "contact_email": request.contact_email,
            "contact_phone": request.contact_phone,
            "state": initial_state,
            "pack_ref": f"{request.country_code}:v{policy.version}",
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
            "decision_id": decision_id,
            "policy_version": policy.version,
        }
        self._projection.apply(TENANT_COMPLIANCE_SUBMITTED_V1, payload)

        return {
            "profile_id": profile_id,
            "state": initial_state,
            "pack_ref": payload["pack_ref"],
            "events": [{"event_type": TENANT_COMPLIANCE_SUBMITTED_V1, "payload": payload}],
        }

    # -- review (approve / reject) -------------------------------

    def review_compliance_profile(
        self, request: ReviewComplianceProfileRequest
    ) -> Optional[RejectionReason]:
        """
        Approve or reject a submitted / under-review compliance profile.

        ``request.decision`` must be "approve" or "reject".
        """
        profile = self._projection.get_profile(request.profile_id)
        if profile is None:
            return RejectionReason(
                code="PROFILE_NOT_FOUND",
                message=f"Compliance profile '{request.profile_id}' not found.",
                policy_name="review_compliance_profile",
            )

        if request.decision not in ("approve", "reject"):
            return RejectionReason(
                code="INVALID_DECISION",
                message="Decision must be 'approve' or 'reject'.",
                policy_name="review_compliance_profile",
            )

        if request.decision == "approve":
            target_state = "verified"
        else:
            target_state = "rejected"

        if not _can_transition(profile.state, target_state):
            return RejectionReason(
                code="INVALID_STATE_TRANSITION",
                message=(
                    f"Cannot transition from '{profile.state}' to '{target_state}'. "
                    f"Valid transitions: {VALID_TRANSITIONS.get(profile.state, [])}."
                ),
                policy_name="review_compliance_profile",
            )

        decision_id = str(uuid.uuid4())
        policy = self._projection.get_policy(profile.country_code)
        policy_version = policy.version if policy else 0

        if request.decision == "approve":
            payload: Dict[str, Any] = {
                "profile_id": request.profile_id,
                "reviewer_id": request.reviewer_id,
                "reason": request.reason,
                "issued_at": request.issued_at,
                "decision_id": decision_id,
                "policy_version": policy_version,
                "tax_id_verified": True,
                "company_reg_verified": True,
                "address_verified": True,
            }
            self._projection.apply(TENANT_COMPLIANCE_APPROVED_V1, payload)
        else:
            payload = {
                "profile_id": request.profile_id,
                "reviewer_id": request.reviewer_id,
                "reason": request.reason,
                "issued_at": request.issued_at,
                "decision_id": decision_id,
                "policy_version": policy_version,
            }
            self._projection.apply(TENANT_COMPLIANCE_REJECTED_V1, payload)

        return None

    # -- activate ------------------------------------------------

    def activate_compliance_profile(
        self, request: ActivateComplianceProfileRequest
    ) -> Optional[RejectionReason]:
        """
        Transition a verified profile to active, enabling billing.
        """
        profile = self._projection.get_profile(request.profile_id)
        if profile is None:
            return RejectionReason(
                code="PROFILE_NOT_FOUND",
                message=f"Compliance profile '{request.profile_id}' not found.",
                policy_name="activate_compliance_profile",
            )

        if not _can_transition(profile.state, "active"):
            return RejectionReason(
                code="INVALID_STATE_TRANSITION",
                message=(
                    f"Cannot activate profile in state '{profile.state}'. "
                    f"Valid transitions: {VALID_TRANSITIONS.get(profile.state, [])}."
                ),
                policy_name="activate_compliance_profile",
            )

        payload: Dict[str, Any] = {
            "profile_id": request.profile_id,
            "actor_id": request.actor_id,
            "issued_at": request.issued_at,
            "decision_id": str(uuid.uuid4()),
        }
        self._projection.apply(TENANT_COMPLIANCE_ACTIVATED_V1, payload)
        return None

    # -- suspend -------------------------------------------------

    def suspend_compliance_profile(
        self, request: SuspendComplianceProfileRequest
    ) -> Optional[RejectionReason]:
        """
        Suspend an active or restricted profile. Disables billing.
        """
        profile = self._projection.get_profile(request.profile_id)
        if profile is None:
            return RejectionReason(
                code="PROFILE_NOT_FOUND",
                message=f"Compliance profile '{request.profile_id}' not found.",
                policy_name="suspend_compliance_profile",
            )

        if not _can_transition(profile.state, "suspended"):
            return RejectionReason(
                code="INVALID_STATE_TRANSITION",
                message=(
                    f"Cannot suspend profile in state '{profile.state}'. "
                    f"Valid transitions: {VALID_TRANSITIONS.get(profile.state, [])}."
                ),
                policy_name="suspend_compliance_profile",
            )

        payload: Dict[str, Any] = {
            "profile_id": request.profile_id,
            "actor_id": request.actor_id,
            "reason": request.reason,
            "issued_at": request.issued_at,
            "decision_id": str(uuid.uuid4()),
        }
        self._projection.apply(TENANT_COMPLIANCE_SUSPENDED_V1, payload)
        return None

    # -- reactivate ----------------------------------------------

    def reactivate_compliance_profile(
        self, request: ReactivateComplianceProfileRequest
    ) -> Optional[RejectionReason]:
        """
        Reactivate a suspended profile. Re-enables billing.
        """
        profile = self._projection.get_profile(request.profile_id)
        if profile is None:
            return RejectionReason(
                code="PROFILE_NOT_FOUND",
                message=f"Compliance profile '{request.profile_id}' not found.",
                policy_name="reactivate_compliance_profile",
            )

        # Reactivation goes to "active" state
        if not _can_transition(profile.state, "active"):
            return RejectionReason(
                code="INVALID_STATE_TRANSITION",
                message=(
                    f"Cannot reactivate profile in state '{profile.state}'. "
                    f"Valid transitions: {VALID_TRANSITIONS.get(profile.state, [])}."
                ),
                policy_name="reactivate_compliance_profile",
            )

        payload: Dict[str, Any] = {
            "profile_id": request.profile_id,
            "actor_id": request.actor_id,
            "reason": request.reason,
            "issued_at": request.issued_at,
            "decision_id": str(uuid.uuid4()),
        }
        self._projection.apply(TENANT_COMPLIANCE_REACTIVATED_V1, payload)
        return None

    # -- block ---------------------------------------------------

    def block_compliance_profile(
        self, request: BlockComplianceProfileRequest
    ) -> Optional[RejectionReason]:
        """
        Block a profile. Only deactivation is possible after this.
        """
        profile = self._projection.get_profile(request.profile_id)
        if profile is None:
            return RejectionReason(
                code="PROFILE_NOT_FOUND",
                message=f"Compliance profile '{request.profile_id}' not found.",
                policy_name="block_compliance_profile",
            )

        if not _can_transition(profile.state, "blocked"):
            return RejectionReason(
                code="INVALID_STATE_TRANSITION",
                message=(
                    f"Cannot block profile in state '{profile.state}'. "
                    f"Valid transitions: {VALID_TRANSITIONS.get(profile.state, [])}."
                ),
                policy_name="block_compliance_profile",
            )

        payload: Dict[str, Any] = {
            "profile_id": request.profile_id,
            "actor_id": request.actor_id,
            "reason": request.reason,
            "issued_at": request.issued_at,
            "decision_id": str(uuid.uuid4()),
        }
        self._projection.apply(TENANT_COMPLIANCE_BLOCKED_V1, payload)
        return None

    # -- auto-verify ---------------------------------------------

    def auto_verify(self, profile_id: str) -> Optional[RejectionReason]:
        """
        Auto-verify a submitted profile for countries that do NOT require
        manual review. Transitions submitted -> verified without a reviewer.

        This is called automatically after submission when the country
        policy has ``manual_review_required=False``.
        """
        profile = self._projection.get_profile(profile_id)
        if profile is None:
            return RejectionReason(
                code="PROFILE_NOT_FOUND",
                message=f"Compliance profile '{profile_id}' not found.",
                policy_name="auto_verify",
            )

        policy = self._projection.get_policy(profile.country_code)
        if policy is not None and policy.manual_review_required:
            return RejectionReason(
                code="MANUAL_REVIEW_REQUIRED",
                message=(
                    f"Country '{profile.country_code}' requires manual review. "
                    "Auto-verification is not permitted."
                ),
                policy_name="auto_verify",
            )

        if not _can_transition(profile.state, "verified"):
            return RejectionReason(
                code="INVALID_STATE_TRANSITION",
                message=(
                    f"Cannot auto-verify profile in state '{profile.state}'. "
                    f"Valid transitions: {VALID_TRANSITIONS.get(profile.state, [])}."
                ),
                policy_name="auto_verify",
            )

        now = datetime.utcnow()
        payload: Dict[str, Any] = {
            "profile_id": profile_id,
            "reviewer_id": "SYSTEM",
            "reason": "Auto-verified: manual review not required for this country.",
            "issued_at": now,
            "decision_id": str(uuid.uuid4()),
            "policy_version": policy.version if policy else 0,
            "tax_id_verified": True,
            "company_reg_verified": True,
            "address_verified": True,
        }
        self._projection.apply(TENANT_COMPLIANCE_APPROVED_V1, payload)
        return None
