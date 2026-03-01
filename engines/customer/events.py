"""
BOS Customer Engine — Event Types
=================================
Hybrid model: Platform Identity (global) + Business Profile (tenant-scoped).
"""

# ── Platform-Level Events (business_id = PLATFORM) ────────────

GLOBAL_CUSTOMER_REGISTERED_V1 = "customer.global.registered.v1"
CLIENT_LINK_REQUESTED_V1 = "customer.link.requested.v1"
CLIENT_LINK_APPROVED_V1 = "customer.link.approved.v1"
CLIENT_LINK_REVOKED_V1 = "customer.link.revoked.v1"
CONSENT_SCOPE_UPDATED_V1 = "customer.consent.scope_updated.v1"

# ── Tenant-Level Events (business_id = actual business) ───────

BUSINESS_CUSTOMER_PROFILE_CREATED_V1 = "customer.profile.created.v1"
BUSINESS_CUSTOMER_PROFILE_UPDATED_V1 = "customer.profile.updated.v1"
BUSINESS_CUSTOMER_SEGMENT_ASSIGNED_V1 = "customer.segment.assigned.v1"

ALL_EVENT_TYPES = (
    GLOBAL_CUSTOMER_REGISTERED_V1,
    CLIENT_LINK_REQUESTED_V1,
    CLIENT_LINK_APPROVED_V1,
    CLIENT_LINK_REVOKED_V1,
    CONSENT_SCOPE_UPDATED_V1,
    BUSINESS_CUSTOMER_PROFILE_CREATED_V1,
    BUSINESS_CUSTOMER_PROFILE_UPDATED_V1,
    BUSINESS_CUSTOMER_SEGMENT_ASSIGNED_V1,
)

# ── Consent Scopes ────────────────────────────────────────────

SCOPE_PROFILE_BASIC = "PROFILE_BASIC"
SCOPE_CONTACT = "CONTACT"
SCOPE_PURCHASE_HISTORY = "PURCHASE_HISTORY"
SCOPE_LOYALTY_POINTS = "LOYALTY_POINTS"
SCOPE_OFFERS = "OFFERS"
SCOPE_MESSAGING = "MESSAGING"

VALID_CONSENT_SCOPES = frozenset({
    SCOPE_PROFILE_BASIC,
    SCOPE_CONTACT,
    SCOPE_PURCHASE_HISTORY,
    SCOPE_LOYALTY_POINTS,
    SCOPE_OFFERS,
    SCOPE_MESSAGING,
})


# ── Payload Builders ──────────────────────────────────────────

def _base_fields(cmd):
    return {
        "business_id": str(cmd.business_id),
        "branch_id": str(cmd.branch_id) if getattr(cmd, "branch_id", None) else None,
        "actor_id": getattr(cmd, "actor_id", None),
        "actor_type": getattr(cmd, "actor_type", None),
        "correlation_id": str(cmd.correlation_id) if hasattr(cmd, "correlation_id") else None,
        "command_id": str(cmd.command_id) if hasattr(cmd, "command_id") else None,
    }


def _global_customer_registered(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "global_customer_id": p["global_customer_id"],
        "phone_hash": p["phone_hash"],
        "registered_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _client_link_requested(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "global_customer_id": p["global_customer_id"],
        "requesting_business_id": p["requesting_business_id"],
        "requested_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _client_link_approved(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "global_customer_id": p["global_customer_id"],
        "approved_business_id": p["approved_business_id"],
        "approved_scopes": p["approved_scopes"],
        "approved_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _client_link_revoked(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "global_customer_id": p["global_customer_id"],
        "revoked_business_id": p["revoked_business_id"],
        "reason": p.get("reason", ""),
        "revoked_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _consent_scope_updated(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "global_customer_id": p["global_customer_id"],
        "target_business_id": p["target_business_id"],
        "new_scopes": p["new_scopes"],
        "updated_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _profile_created(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "global_customer_id": p["global_customer_id"],
        "display_name": p.get("display_name", ""),
        "approved_scopes": p.get("approved_scopes", []),
        "created_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _profile_updated(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "changes": p["changes"],
        "updated_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


def _segment_assigned(cmd):
    base = _base_fields(cmd)
    p = cmd.payload
    base.update({
        "business_customer_id": p["business_customer_id"],
        "segment": p["segment"],
        "assigned_at": p.get("issued_at") or str(cmd.issued_at),
    })
    return base


PAYLOAD_BUILDERS = {
    GLOBAL_CUSTOMER_REGISTERED_V1: _global_customer_registered,
    CLIENT_LINK_REQUESTED_V1: _client_link_requested,
    CLIENT_LINK_APPROVED_V1: _client_link_approved,
    CLIENT_LINK_REVOKED_V1: _client_link_revoked,
    CONSENT_SCOPE_UPDATED_V1: _consent_scope_updated,
    BUSINESS_CUSTOMER_PROFILE_CREATED_V1: _profile_created,
    BUSINESS_CUSTOMER_PROFILE_UPDATED_V1: _profile_updated,
    BUSINESS_CUSTOMER_SEGMENT_ASSIGNED_V1: _segment_assigned,
}

COMMAND_TO_EVENT_TYPE = {
    "customer.global.register.request": GLOBAL_CUSTOMER_REGISTERED_V1,
    "customer.link.request.request": CLIENT_LINK_REQUESTED_V1,
    "customer.link.approve.request": CLIENT_LINK_APPROVED_V1,
    "customer.link.revoke.request": CLIENT_LINK_REVOKED_V1,
    "customer.consent.update_scope.request": CONSENT_SCOPE_UPDATED_V1,
    "customer.profile.create.request": BUSINESS_CUSTOMER_PROFILE_CREATED_V1,
    "customer.profile.update.request": BUSINESS_CUSTOMER_PROFILE_UPDATED_V1,
    "customer.segment.assign.request": BUSINESS_CUSTOMER_SEGMENT_ASSIGNED_V1,
}


def register_customer_event_types(registry):
    for event_type, builder in PAYLOAD_BUILDERS.items():
        registry.register(event_type, builder)


def resolve_customer_event_type(name: str):
    return PAYLOAD_BUILDERS.get(name)
