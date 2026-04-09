"""
BOS Agent Contract Service
==========================
Service functions for Platform-RLA franchise agreements.

BOS Doctrine (Franchisor Model):
  - Platform = Franchisor. RLA = Franchisee with guided autonomy.
  - Contracts have HARDCODED terms (non-negotiable) + GENERATED terms (set at appointment).
  - Three termination outcomes:
      REVERSIBLE   — violation, reinstatement possible to full terms
      PERMANENT    — serious breach, licence revoked permanently
      REDUCED      — reinstated at lower commission share under fixed term
  - During any RLA termination: tenants continue service without billing
    until a new RLA is assigned to the region.
  - Region exclusivity: one ACTIVE RLA per region at all times.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any


# --------------------------------------------------------------------------- #
# Hardcoded platform terms — these NEVER change regardless of negotiation
# --------------------------------------------------------------------------- #

PLATFORM_HARDCODED_TERMS: dict[str, Any] = {
    "remittance_deadline_days": 5,
    "tenant_continuity_guaranteed": True,
    "region_exclusivity": True,
    "platform_audit_right": True,
    "compliance_ownership_by_rla": True,
    "sub_agent_requires_platform_approval": True,
    "price_bound_enforcement": True,
    "commission_on_all_regional_tenants": True,
    "platform_can_terminate_with_notice_days": 30,
    "dispute_resolution": "BOS_PLATFORM_ARBITRATION",
    "governing_law": "Laws of the Republic of Kenya",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_contract(contract: Any) -> dict[str, Any]:
    return {
        "contract_id": str(contract.contract_id),
        "agent_id": str(contract.agent_id),
        "agent_name": contract.agent_name,
        "region_code": contract.region_code,
        "status": contract.status,
        "version": contract.version,
        "termination_type": contract.termination_type,
        "termination_reason": contract.termination_reason,
        "terminated_at": contract.terminated_at.isoformat() if contract.terminated_at else None,
        "hardcoded_terms": contract.hardcoded_terms,
        "generated_terms": contract.generated_terms,
        "reduced_commission_rate": str(contract.reduced_commission_rate) if contract.reduced_commission_rate else None,
        "reduced_commission_term_months": contract.reduced_commission_term_months,
        "reduced_commission_expires_at": contract.reduced_commission_expires_at.isoformat() if contract.reduced_commission_expires_at else None,
        "generated_at": contract.generated_at.isoformat() if contract.generated_at else None,
        "signed_at": contract.signed_at.isoformat() if contract.signed_at else None,
        "signed_by_name": contract.signed_by_name,
        "expires_at": contract.expires_at.isoformat() if contract.expires_at else None,
        "region_pending_rla_since": contract.region_pending_rla_since.isoformat() if contract.region_pending_rla_since else None,
        "notes": contract.notes,
        "created_at": contract.created_at.isoformat(),
    }


def generate_agent_contract(
    agent_id: str,
    agent_name: str,
    region_code: str,
    commission_rate: float,
    max_platform_discount_pct: int,
    max_trial_days: int,
    contract_duration_months: int = 24,
    monthly_tenant_target: int = 0,
    monthly_revenue_target: int = 0,
    generated_by: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """
    Generate a new franchise contract for an RLA.
    Status starts as DRAFT — must be sent and signed before activation.
    """
    from core.saas.models import AgentContract, AgentContractStatus

    # Region exclusivity: only one ACTIVE or DRAFT contract per region
    existing = AgentContract.objects.filter(
        region_code=region_code,
        status__in=[AgentContractStatus.ACTIVE, AgentContractStatus.DRAFT],
    ).first()
    if existing:
        raise ValueError(
            f"Region {region_code} already has an active/pending contract "
            f"(contract_id={existing.contract_id}). "
            "Terminate the existing contract before generating a new one."
        )

    now = _now()
    expires_at = now + timedelta(days=contract_duration_months * 30)

    generated_terms: dict[str, Any] = {
        "commission_rate": commission_rate,
        "max_platform_discount_pct": max_platform_discount_pct,
        "max_trial_days": max_trial_days,
        "contract_duration_months": contract_duration_months,
        "performance_targets": {
            "monthly_tenant_target": monthly_tenant_target,
            "monthly_revenue_target": monthly_revenue_target,
        },
    }

    contract = AgentContract.objects.create(
        agent_id=uuid.UUID(agent_id),
        agent_name=agent_name,
        region_code=region_code,
        status=AgentContractStatus.DRAFT,
        version=1,
        hardcoded_terms=PLATFORM_HARDCODED_TERMS,
        generated_terms=generated_terms,
        generated_at=now,
        expires_at=expires_at,
        generated_by=uuid.UUID(generated_by) if generated_by else None,
        notes=notes,
    )
    return _serialize_contract(contract)


def sign_agent_contract(
    contract_id: str,
    signed_by_name: str,
) -> dict[str, Any]:
    """RLA signs the contract — status moves from DRAFT → ACTIVE."""
    from core.saas.models import AgentContract, AgentContractStatus

    try:
        contract = AgentContract.objects.get(contract_id=contract_id)
    except AgentContract.DoesNotExist:
        raise ValueError(f"Contract {contract_id} not found.")

    if contract.status != AgentContractStatus.DRAFT:
        raise ValueError(
            f"Contract {contract_id} cannot be signed in status '{contract.status}'. "
            "Only DRAFT contracts can be signed."
        )

    now = _now()
    contract.status = AgentContractStatus.ACTIVE
    contract.signed_at = now
    contract.signed_by_name = signed_by_name
    contract.sent_to_agent_at = contract.sent_to_agent_at or now
    contract.save(update_fields=["status", "signed_at", "signed_by_name", "sent_to_agent_at", "updated_at"])
    return _serialize_contract(contract)


def terminate_agent_contract_reversible(
    agent_id: str,
    reason: str,
    terminated_by: str | None = None,
) -> dict[str, Any]:
    """
    REVERSIBLE termination — violation that can be remedied.
    Region enters PENDING state: tenants continue without billing.
    RLA can be reinstated to full terms once remedied.
    """
    from core.saas.models import AgentContract, AgentContractStatus, TerminationType

    contract = _get_active_contract(agent_id)
    now = _now()
    contract.status = AgentContractStatus.TERMINATED_REVERSIBLE
    contract.termination_type = TerminationType.REVERSIBLE
    contract.termination_reason = reason
    contract.terminated_at = now
    contract.terminated_by = uuid.UUID(terminated_by) if terminated_by else None
    contract.region_pending_rla_since = now
    contract.save(update_fields=[
        "status", "termination_type", "termination_reason",
        "terminated_at", "terminated_by", "region_pending_rla_since", "updated_at",
    ])
    return _serialize_contract(contract)


def terminate_agent_contract_permanent(
    agent_id: str,
    reason: str,
    terminated_by: str | None = None,
) -> dict[str, Any]:
    """
    PERMANENT termination — serious breach, licence revoked forever.
    This RLA can NEVER be reinstated. A new RLA must be appointed for the region.
    """
    from core.saas.models import AgentContract, AgentContractStatus, TerminationType

    contract = _get_active_contract(agent_id)
    now = _now()
    contract.status = AgentContractStatus.TERMINATED_PERMANENT
    contract.termination_type = TerminationType.PERMANENT
    contract.termination_reason = reason
    contract.terminated_at = now
    contract.terminated_by = uuid.UUID(terminated_by) if terminated_by else None
    contract.region_pending_rla_since = now
    contract.save(update_fields=[
        "status", "termination_type", "termination_reason",
        "terminated_at", "terminated_by", "region_pending_rla_since", "updated_at",
    ])
    return _serialize_contract(contract)


def reinstate_agent_contract_full(
    agent_id: str,
    reinstated_by: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """
    Full reinstatement — restores RLA to ACTIVE under original terms.
    Only applicable when contract is TERMINATED_REVERSIBLE.
    Clears region_pending_rla_since (billing resumes immediately).
    """
    from core.saas.models import AgentContract, AgentContractStatus

    try:
        contract = AgentContract.objects.filter(
            agent_id=uuid.UUID(agent_id),
            status=AgentContractStatus.TERMINATED_REVERSIBLE,
        ).order_by("-created_at").first()
    except Exception:
        contract = None

    if not contract:
        raise ValueError(
            f"No reversibly-terminated contract found for agent {agent_id}. "
            "Only TERMINATED_REVERSIBLE contracts can be fully reinstated."
        )

    contract.status = AgentContractStatus.ACTIVE
    contract.termination_type = ""
    contract.termination_reason = ""
    contract.terminated_at = None
    contract.terminated_by = None
    contract.region_pending_rla_since = None
    if notes:
        contract.notes = (contract.notes + f"\n[Reinstated] {notes}").strip()
    contract.save(update_fields=[
        "status", "termination_type", "termination_reason",
        "terminated_at", "terminated_by", "region_pending_rla_since", "notes", "updated_at",
    ])
    return _serialize_contract(contract)


def reinstate_agent_contract_reduced(
    agent_id: str,
    reduced_commission_rate: float,
    reduced_commission_term_months: int,
    reason: str = "",
    reinstated_by: str | None = None,
) -> dict[str, Any]:
    """
    Reduced-commission reinstatement — RLA reinstated but with a lower commission
    share for a fixed term. After the term expires, full rates resume (or contract
    is renegotiated). Status = REDUCED_COMMISSION.

    Applies when: TERMINATED_REVERSIBLE and platform decides partial reinstatement.
    """
    from core.saas.models import AgentContract, AgentContractStatus, TerminationType
    from decimal import Decimal

    try:
        contract = AgentContract.objects.filter(
            agent_id=uuid.UUID(agent_id),
            status=AgentContractStatus.TERMINATED_REVERSIBLE,
        ).order_by("-created_at").first()
    except Exception:
        contract = None

    if not contract:
        raise ValueError(
            f"No reversibly-terminated contract found for agent {agent_id}."
        )

    now = _now()
    expires_at = now + timedelta(days=reduced_commission_term_months * 30)

    contract.status = AgentContractStatus.REDUCED_COMMISSION
    contract.termination_type = TerminationType.REDUCED_COMMISSION
    contract.termination_reason = reason or contract.termination_reason
    contract.region_pending_rla_since = None
    contract.reduced_commission_rate = Decimal(str(reduced_commission_rate))
    contract.reduced_commission_term_months = reduced_commission_term_months
    contract.reduced_commission_expires_at = expires_at
    if reason:
        contract.notes = (contract.notes + f"\n[Reduced reinstatement] {reason}").strip()
    contract.save(update_fields=[
        "status", "termination_type", "termination_reason",
        "region_pending_rla_since", "reduced_commission_rate",
        "reduced_commission_term_months", "reduced_commission_expires_at",
        "notes", "updated_at",
    ])
    return _serialize_contract(contract)


def get_agent_contract(agent_id: str) -> dict[str, Any] | None:
    """Get the most recent contract for an agent."""
    from core.saas.models import AgentContract

    contract = AgentContract.objects.filter(
        agent_id=uuid.UUID(agent_id),
    ).order_by("-created_at").first()
    return _serialize_contract(contract) if contract else None


def list_pending_regions() -> list[dict[str, Any]]:
    """
    List all regions currently in PENDING_RLA state
    (i.e. RLA terminated, no replacement yet assigned).
    Tenants in these regions continue service without billing.
    """
    from core.saas.models import AgentContract

    contracts = AgentContract.objects.filter(
        region_pending_rla_since__isnull=False,
    ).order_by("region_pending_rla_since")

    return [
        {
            "region_code": c.region_code,
            "agent_name": c.agent_name,
            "termination_type": c.termination_type,
            "pending_since": c.region_pending_rla_since.isoformat(),
            "contract_id": str(c.contract_id),
        }
        for c in contracts
    ]


def _get_active_contract(agent_id: str) -> Any:
    """
    Fetch the current active/suspended contract for an agent.
    Raises ValueError if none found.
    """
    from core.saas.models import AgentContract, AgentContractStatus

    contract = AgentContract.objects.filter(
        agent_id=uuid.UUID(agent_id),
        status__in=[
            AgentContractStatus.ACTIVE,
            AgentContractStatus.SUSPENDED,
            AgentContractStatus.REDUCED_COMMISSION,
        ],
    ).order_by("-created_at").first()

    if not contract:
        raise ValueError(
            f"No active contract found for agent {agent_id}. "
            "Generate and activate a contract first."
        )
    return contract
