"""
BOS RLA Health Score Service
=============================
Computes a composite 0-100 health score for each Region License Agent.

Components (total 100 pts):
  remittance_score  (40 pts) — on-time remittance compliance
  growth_score      (25 pts) — tenant growth vs monthly target
  escalation_score  (20 pts) — open/unresolved escalation ratio
  activity_score    (15 pts) — days since last active

Grades:
  GREEN  80–100  Healthy
  AMBER  60–79   Watch
  ORANGE 40–59   At Risk
  RED    20–39   Action Required
  BLACK  0–19    Critical / Suspended

BOS Doctrine:
  Health score drives Platform oversight decisions.
  AGENT_MANAGER can view all scores.
  Score below ORANGE triggers auto-escalation alert.
  Score BLACK triggers Tier 1 review requirement before next payout.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _grade(score: int) -> str:
    if score >= 80: return "GREEN"
    if score >= 60: return "AMBER"
    if score >= 40: return "ORANGE"
    if score >= 20: return "RED"
    return "BLACK"


def compute_health_score(
    agent_id: str,
    region_code: str,
    overdue_remittances: int,
    total_remittances: int,
    active_tenants: int,
    tenant_target: int,
    open_escalations: int,
    total_escalations: int,
    days_since_active: int,
) -> dict[str, Any]:
    """
    Compute health score from raw inputs. Does NOT persist — call
    save_health_score() to persist.
    """
    # ── 1. Remittance Score (40 pts) ──────────────────────────────────────
    # Full 40 pts if zero overdue. Deduct proportionally.
    if total_remittances == 0:
        remittance_score = 40  # no history → full score (new agent)
    else:
        compliance_rate = max(0.0, 1.0 - (overdue_remittances / total_remittances))
        remittance_score = round(40 * compliance_rate)

    # ── 2. Growth Score (25 pts) ──────────────────────────────────────────
    # Full 25 pts if tenant count >= target. 0 pts if 0 tenants and target > 0.
    if tenant_target <= 0:
        growth_score = 20  # no target set → partial credit
    else:
        ratio = min(1.0, active_tenants / tenant_target)
        growth_score = round(25 * ratio)

    # ── 3. Escalation Score (20 pts) ──────────────────────────────────────
    # Full 20 pts if no open escalations. 0 pts if all escalations open.
    if total_escalations == 0:
        escalation_score = 20
    else:
        resolved = total_escalations - open_escalations
        resolution_rate = max(0.0, resolved / total_escalations)
        # Also penalise if open count is high (> 5 open = 0 pts regardless)
        if open_escalations > 5:
            escalation_score = 0
        else:
            escalation_score = round(20 * resolution_rate)

    # ── 4. Activity Score (15 pts) ────────────────────────────────────────
    # Full 15 pts if active within 7 days.
    # 0 pts if inactive > 60 days.
    if days_since_active <= 7:
        activity_score = 15
    elif days_since_active <= 30:
        activity_score = 10
    elif days_since_active <= 60:
        activity_score = 5
    else:
        activity_score = 0

    total_score = remittance_score + growth_score + escalation_score + activity_score
    grade = _grade(total_score)

    return {
        "agent_id": agent_id,
        "region_code": region_code,
        "total_score": total_score,
        "grade": grade,
        "remittance_score": remittance_score,
        "growth_score": growth_score,
        "escalation_score": escalation_score,
        "activity_score": activity_score,
        "overdue_remittances": overdue_remittances,
        "active_tenants": active_tenants,
        "tenant_target": tenant_target,
        "open_escalations": open_escalations,
        "days_since_active": days_since_active,
    }


def save_health_score(
    agent_id: str,
    region_code: str,
    period: str,
    score_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Persist (upsert) a health score for agent + period.
    Returns the serialised score record.
    """
    from core.saas.models import SaaSRlaHealthScore

    obj, _ = SaaSRlaHealthScore.objects.update_or_create(
        agent_id=agent_id,
        period=period,
        defaults={
            "region_code": region_code,
            "total_score": score_data["total_score"],
            "grade": score_data["grade"],
            "remittance_score": score_data["remittance_score"],
            "growth_score": score_data["growth_score"],
            "escalation_score": score_data["escalation_score"],
            "activity_score": score_data["activity_score"],
            "overdue_remittances": score_data["overdue_remittances"],
            "active_tenants": score_data["active_tenants"],
            "tenant_target": score_data["tenant_target"],
            "open_escalations": score_data["open_escalations"],
            "days_since_active": score_data["days_since_active"],
        },
    )
    return _serialize_health(obj)


def get_health_score(agent_id: str, period: str | None = None) -> dict[str, Any] | None:
    """Get the latest (or period-specific) health score for an agent."""
    from core.saas.models import SaaSRlaHealthScore

    qs = SaaSRlaHealthScore.objects.filter(agent_id=agent_id)
    if period:
        qs = qs.filter(period=period)
    obj = qs.order_by("-period").first()
    return _serialize_health(obj) if obj else None


def list_health_scores(period: str | None = None, grade: str | None = None) -> list[dict[str, Any]]:
    """List all RLA health scores, optionally filtered by period or grade."""
    from core.saas.models import SaaSRlaHealthScore

    qs = SaaSRlaHealthScore.objects.all()
    if period:
        qs = qs.filter(period=period)
    if grade:
        qs = qs.filter(grade=grade)
    return [_serialize_health(obj) for obj in qs.order_by("-total_score")]


def refresh_agent_health_score(agent_id: str, period: str | None = None) -> dict[str, Any]:
    """
    Compute and save a fresh health score for an agent by pulling live data
    from the DB. Used by Platform Admin or automated job.
    """
    from core.saas.models import SaaSRlaHealthScore
    from core.saas.contracts import get_agent_contract

    now = _now()
    if not period:
        period = now.strftime("%Y-%m")

    # Get contract to find region + target
    contract = get_agent_contract(agent_id)
    region_code = contract["region_code"] if contract else ""
    tenant_target = 0
    if contract and contract.get("generated_terms"):
        perf = contract["generated_terms"].get("performance_targets", {})
        tenant_target = perf.get("monthly_tenant_target", 0)

    # Count overdue remittances
    overdue_remittances = 0
    total_remittances = 0
    try:
        from core.saas.models import SaaSLedgerEntry
        from datetime import timedelta
        deadline = now - timedelta(days=5)
        entries = SaaSLedgerEntry.objects.filter(rla_id=agent_id)
        total_remittances = entries.count()
        overdue_remittances = entries.filter(
            status="RECORDED",
            created_at__lt=deadline,
        ).count()
    except Exception:
        pass

    # Count active tenants
    active_tenants = 0
    try:
        from core.saas.models import SaaSSubscription
        active_tenants = SaaSSubscription.objects.filter(
            status__in=["ACTIVE", "TRIAL"],
        ).count()
        # Ideally filter by region — using region_code from contract
    except Exception:
        pass

    # Count escalations
    open_escalations = 0
    total_escalations = 0
    try:
        from core.saas.models import SaaSEscalation
        qs = SaaSEscalation.objects.filter(agent_id=agent_id)
        total_escalations = qs.count()
        open_escalations = qs.filter(status="OPEN").count()
    except Exception:
        pass

    # Days since active — from agent record
    days_since_active = 0
    try:
        from core.saas.models import SaaSAgent
        agent = SaaSAgent.objects.filter(agent_id=agent_id).first()
        if agent and agent.last_active_at:
            days_since_active = (now - agent.last_active_at).days
        elif agent and agent.created_at:
            days_since_active = (now - agent.created_at).days
    except Exception:
        pass

    score_data = compute_health_score(
        agent_id=agent_id,
        region_code=region_code,
        overdue_remittances=overdue_remittances,
        total_remittances=total_remittances,
        active_tenants=active_tenants,
        tenant_target=tenant_target,
        open_escalations=open_escalations,
        total_escalations=total_escalations,
        days_since_active=days_since_active,
    )
    return save_health_score(agent_id, region_code, period, score_data)


def _serialize_health(obj: Any) -> dict[str, Any]:
    return {
        "id": str(obj.id),
        "agent_id": str(obj.agent_id),
        "region_code": obj.region_code,
        "period": obj.period,
        "total_score": obj.total_score,
        "grade": obj.grade,
        "remittance_score": obj.remittance_score,
        "growth_score": obj.growth_score,
        "escalation_score": obj.escalation_score,
        "activity_score": obj.activity_score,
        "overdue_remittances": obj.overdue_remittances,
        "active_tenants": obj.active_tenants,
        "tenant_target": obj.tenant_target,
        "open_escalations": obj.open_escalations,
        "days_since_active": obj.days_since_active,
        "computed_at": obj.computed_at.isoformat(),
    }
