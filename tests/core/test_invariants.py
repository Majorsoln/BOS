"""
BOS Invariant Tests (GAP-12)
==============================
Cross-cutting tests that verify BOS doctrine rules hold
across the entire codebase. These are architectural invariants
that must never be violated.
"""

import importlib
import inspect
import uuid
from datetime import datetime, timezone
from dataclasses import fields, FrozenInstanceError

import pytest


# ══════════════════════════════════════════════════════════════
# INVARIANT 1: All core models are frozen (immutable)
# ══════════════════════════════════════════════════════════════

FROZEN_MODELS = [
    "core.audit.models.AuditEntry",
    "core.audit.models.ConsentRecord",
    "core.business.models.Business",
    "core.business.models.Branch",
    "core.config.rules.TaxRule",
    "core.config.rules.ComplianceRule",
    "core.time.temporal.TimeWindow",
    "core.commands.rejection.RejectionReason",
    "core.security.access.AccessDecision",
]


@pytest.mark.parametrize("model_path", FROZEN_MODELS)
def test_core_models_are_frozen(model_path):
    """Every core model dataclass must be frozen (immutable)."""
    module_path, class_name = model_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)

    # Check it's a dataclass with frozen=True
    assert hasattr(cls, "__dataclass_fields__"), f"{model_path} is not a dataclass"
    assert cls.__dataclass_params__.frozen, f"{model_path} is not frozen"


# ══════════════════════════════════════════════════════════════
# INVARIANT 2: All __init__.py have __all__ exports
# ══════════════════════════════════════════════════════════════

CORE_MODULES = [
    "core.time",
    "core.audit",
    "core.business",
    "core.config",
    "core.resilience",
    "core.security",
    "core.commands",
    "core.context",
]


@pytest.mark.parametrize("module_path", CORE_MODULES)
def test_core_modules_have_all_exports(module_path):
    """Every core module __init__.py must define __all__."""
    module = importlib.import_module(module_path)
    assert hasattr(module, "__all__"), f"{module_path} missing __all__"
    assert len(module.__all__) > 0, f"{module_path} has empty __all__"


# ══════════════════════════════════════════════════════════════
# INVARIANT 3: RejectionReason always has required fields
# ══════════════════════════════════════════════════════════════

def test_rejection_reason_requires_code_message_policy():
    """RejectionReason must enforce code, message, policy_name."""
    from core.commands.rejection import RejectionReason

    # Valid
    r = RejectionReason(code="TEST", message="test msg", policy_name="test_policy")
    assert r.code == "TEST"

    # Missing code
    with pytest.raises(ValueError):
        RejectionReason(code="", message="test", policy_name="p")

    # Missing message
    with pytest.raises(ValueError):
        RejectionReason(code="C", message="", policy_name="p")

    # Missing policy
    with pytest.raises(ValueError):
        RejectionReason(code="C", message="m", policy_name="")


# ══════════════════════════════════════════════════════════════
# INVARIANT 4: BusinessContext requires UUID business_id
# ══════════════════════════════════════════════════════════════

def test_business_context_requires_uuid():
    """BusinessContext must reject non-UUID business_id."""
    from core.context.business_context import BusinessContext

    # Valid
    ctx = BusinessContext(business_id=uuid.uuid4())
    assert ctx.business_id is not None

    # Invalid
    with pytest.raises(ValueError, match="UUID"):
        BusinessContext(business_id="not-a-uuid")


# ══════════════════════════════════════════════════════════════
# INVARIANT 5: ActorContext requires non-empty actor_type/id
# ══════════════════════════════════════════════════════════════

def test_actor_context_requires_nonempty_fields():
    """ActorContext must reject empty actor_type and actor_id."""
    from core.context.actor_context import ActorContext

    # Valid
    ctx = ActorContext(actor_type="HUMAN", actor_id="user-1")
    assert ctx.actor_type == "HUMAN"

    # Empty type
    with pytest.raises(ValueError):
        ActorContext(actor_type="", actor_id="user-1")

    # Empty id
    with pytest.raises(ValueError):
        ActorContext(actor_type="HUMAN", actor_id="")


# ══════════════════════════════════════════════════════════════
# INVARIANT 6: Clock protocol — FixedClock is deterministic
# ══════════════════════════════════════════════════════════════

def test_fixed_clock_determinism():
    """FixedClock must return exact same value every call."""
    from core.time.clock import FixedClock

    fixed_dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    clock = FixedClock(fixed_dt)
    results = [clock.now_utc() for _ in range(100)]
    assert all(r == fixed_dt for r in results)


# ══════════════════════════════════════════════════════════════
# INVARIANT 7: TaxRule rate bounds [0, 1]
# ══════════════════════════════════════════════════════════════

def test_tax_rule_rate_bounds():
    """Tax rate must be between 0 and 1."""
    from core.config.rules import TaxRule

    # Valid bounds
    TaxRule(country_code="KE", tax_type="VAT", rate=0.0)
    TaxRule(country_code="KE", tax_type="VAT", rate=1.0)

    # Out of bounds
    with pytest.raises(ValueError):
        TaxRule(country_code="KE", tax_type="VAT", rate=1.01)
    with pytest.raises(ValueError):
        TaxRule(country_code="KE", tax_type="VAT", rate=-0.01)


# ══════════════════════════════════════════════════════════════
# INVARIANT 8: Resilience mode transitions
# ══════════════════════════════════════════════════════════════

def test_resilience_mode_write_blocked_in_degraded():
    """Writes must be rejected in non-NORMAL resilience modes."""
    from core.resilience import SystemHealth, check_resilience

    health = SystemHealth()

    # NORMAL: writes OK
    assert check_resilience(health, is_write=True) is None

    # DEGRADED: writes blocked
    health.set_degraded("test")
    rejection = check_resilience(health, is_write=True)
    assert rejection is not None

    # READ_ONLY: writes blocked
    health.set_read_only("test")
    rejection = check_resilience(health, is_write=True)
    assert rejection is not None

    # Recover: writes OK again
    health.recover()
    assert check_resilience(health, is_write=True) is None


# ══════════════════════════════════════════════════════════════
# INVARIANT 9: Audit entries are append-only (no mutation)
# ══════════════════════════════════════════════════════════════

def test_audit_entry_immutability():
    """AuditEntry fields cannot be modified after creation."""
    from core.audit.models import AuditEntry

    entry = AuditEntry(
        entry_id=uuid.uuid4(),
        event_id=uuid.uuid4(),
        actor_id="u1",
        actor_type="HUMAN",
        action="test",
        resource_type="T",
        resource_id="t1",
        business_id=uuid.uuid4(),
        branch_id=None,
        status="EXECUTED",
        occurred_at=datetime.now(timezone.utc),
    )
    with pytest.raises((AttributeError, FrozenInstanceError)):
        entry.status = "REJECTED"
    with pytest.raises((AttributeError, FrozenInstanceError)):
        entry.actor_id = "hacker"


# ══════════════════════════════════════════════════════════════
# INVARIANT 10: Consent revocation creates new record
# ══════════════════════════════════════════════════════════════

def test_consent_revocation_is_non_destructive():
    """Revoking consent must create a NEW record, not mutate the original."""
    from core.audit.functions import grant_consent, revoke_consent

    original = grant_consent(
        subject_id="user-1",
        consent_type="BIOMETRIC_CAPTURE",
        business_id=uuid.uuid4(),
        granted_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    revoked = revoke_consent(
        original,
        revoked_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )

    # Original is untouched
    assert original.revoked_at is None
    assert original.is_valid(datetime(2025, 3, 1, tzinfo=timezone.utc))

    # Revoked record reflects revocation
    assert revoked.revoked_at is not None
    assert not revoked.is_valid(datetime(2025, 7, 1, tzinfo=timezone.utc))

    # Same consent_id (it's the same consent, just revoked)
    assert revoked.consent_id == original.consent_id


# ══════════════════════════════════════════════════════════════
# INVARIANT 11: Security stubs are permissive (Phase 8 not enforced)
# ══════════════════════════════════════════════════════════════

def test_security_stubs_permissive():
    """Phase 8 security stubs must be permissive (no false denials)."""
    from core.security import check_access, RateLimiter

    # Access check always grants
    decision = check_access(
        actor_id="anyone",
        permission="anything",
        business_id=uuid.uuid4(),
    )
    assert decision.granted

    # Rate limiter always allows
    limiter = RateLimiter()
    result = limiter.check("anyone", uuid.uuid4())
    assert result.allowed
