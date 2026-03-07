"""
BOS Django Adapter Wiring
=========================
Constructs HttpApiDependencies for local/staging live runs.

This module is adapter-only glue:
- no core contract changes
- no replay/event-store logic changes
"""

from __future__ import annotations

import threading
import uuid
from typing import Any

from core.auth.provider import DbAuthProvider
from core.auth.service import ApiKeyService, hash_api_key
from core.admin.projections import AdminProjectionStore
from core.admin.repository import (
    AdminRepository,
    RepositoryComplianceProvider,
    RepositoryDocumentProvider,
    RepositoryFeatureFlagProvider,
)
from core.admin.service import AdminDataService
from core.bootstrap.subscription_wiring import wire_all_subscriptions
from core.commands.bus import CommandBus
from core.commands.dispatcher import CommandDispatcher
from core.context.business_context import BusinessContext
from core.document_issuance.projections import DocumentIssuanceProjectionStore
from core.document_issuance.registry import is_document_issuance_event_type
from core.document_issuance.repository import DocumentIssuanceRepository
from core.document_issuance.service import DocumentIssuanceService
from core.documents.numbering.models import NumberingPolicy
from core.documents.numbering.provider import InMemoryNumberingProvider
from core.events import SubscriberRegistry
from core.event_store.persistence import (
    load_events_for_business,
    persist_event,
)
from core.event_store.validators.registry import EventTypeRegistry
from core.http_api.dependencies import HttpApiDependencies, UtcClock, UuidIdProvider
from core.identity_store.models import Business as _BusinessModel
from core.identity_store.service import (
    DEFAULT_CASHIER_ROLE,
    assign_role as assign_identity_role,
    bootstrap_identity as bootstrap_identity_store,
)
from core.permissions import DbPermissionProvider


DEV_ADMIN_API_KEY = "dev-admin-key"
DEV_CASHIER_API_KEY = "dev-cashier-key"

DEV_BUSINESS_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DEV_ADMIN_BRANCH_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEV_CASHIER_BRANCH_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")

_DEV_ADMIN_ACTOR_ID = "live-admin-user"
_DEV_CASHIER_ACTOR_ID = "live-cashier-user"

_DEPENDENCIES_LOCK = threading.Lock()
_DEPENDENCIES: HttpApiDependencies | None = None


def _coerce_uuid_or_passthrough(value: Any) -> Any:
    if value is None or isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except ValueError:
            return value
    return value


def _normalize_admin_event_for_projection(
    event_data: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(event_data.get("payload", {}))
    payload["business_id"] = _coerce_uuid_or_passthrough(payload.get("business_id"))
    payload["branch_id"] = _coerce_uuid_or_passthrough(payload.get("branch_id"))

    normalized = dict(event_data)
    normalized["business_id"] = _coerce_uuid_or_passthrough(
        normalized.get("business_id")
    )
    normalized["branch_id"] = _coerce_uuid_or_passthrough(normalized.get("branch_id"))
    normalized["payload"] = payload
    return normalized


def _rebuild_admin_projection_store_from_events(
    projection_store: AdminProjectionStore,
    business_id: uuid.UUID,
) -> None:
    for event_data in load_events_for_business(business_id):
        event_type = event_data.get("event_type")
        if not isinstance(event_type, str) or not event_type.startswith("admin."):
            continue
        projection_store.apply(_normalize_admin_event_for_projection(event_data))


def _normalize_document_issuance_payload_for_projection(
    payload: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["business_id"] = _coerce_uuid_or_passthrough(
        normalized.get("business_id")
    )
    normalized["branch_id"] = _coerce_uuid_or_passthrough(
        normalized.get("branch_id")
    )
    normalized["document_id"] = _coerce_uuid_or_passthrough(
        normalized.get("document_id")
    )
    normalized["correlation_id"] = _coerce_uuid_or_passthrough(
        normalized.get("correlation_id")
    )
    return normalized


def _rebuild_document_issuance_projection_store_from_events(
    projection_store: DocumentIssuanceProjectionStore,
    business_id: uuid.UUID,
) -> None:
    for event_data in load_events_for_business(business_id):
        event_type = event_data.get("event_type")
        if not isinstance(event_type, str):
            continue
        if not is_document_issuance_event_type(event_type):
            continue

        payload = event_data.get("payload")
        if not isinstance(payload, dict):
            continue

        projection_store.apply(
            event_type=event_type,
            payload=_normalize_document_issuance_payload_for_projection(payload),
        )


def _build_business_context() -> BusinessContext:
    known_branches = frozenset({DEV_ADMIN_BRANCH_ID, DEV_CASHIER_BRANCH_ID})

    def _branch_checker(branch_id: uuid.UUID, business_id: uuid.UUID) -> bool:
        return business_id == DEV_BUSINESS_ID and branch_id in known_branches

    return BusinessContext(
        business_id=DEV_BUSINESS_ID,
        branch_id=None,
        _branch_ownership_checker=_branch_checker,
    )


def _build_permission_provider() -> DbPermissionProvider:
    return DbPermissionProvider()


def _ensure_dev_identity_records() -> None:
    bootstrap_identity_store(
        business_id=DEV_BUSINESS_ID,
        business_name="BOS Dev Business",
        default_currency="USD",
        default_language="en",
        branches=(
            {
                "branch_id": str(DEV_ADMIN_BRANCH_ID),
                "name": "ADMIN",
                "timezone": "UTC",
            },
            {
                "branch_id": str(DEV_CASHIER_BRANCH_ID),
                "name": "CASHIER",
                "timezone": "UTC",
            },
        ),
        admin_actor_id=_DEV_ADMIN_ACTOR_ID,
        cashier_actor_id=None,
    )
    assign_identity_role(
        business_id=DEV_BUSINESS_ID,
        actor_id=_DEV_CASHIER_ACTOR_ID,
        actor_type="USER",
        role_name=DEFAULT_CASHIER_ROLE,
        branch_id=DEV_CASHIER_BRANCH_ID,
        display_name=_DEV_CASHIER_ACTOR_ID,
    )


def _ensure_dev_api_key_credentials() -> None:
    credential_specs = (
        {
            "api_key": DEV_ADMIN_API_KEY,
            "actor_id": _DEV_ADMIN_ACTOR_ID,
            "actor_type": "USER",
            "allowed_business_ids": (str(DEV_BUSINESS_ID),),
            "allowed_branch_ids_by_business": {
                str(DEV_BUSINESS_ID): (
                    str(DEV_ADMIN_BRANCH_ID),
                    str(DEV_CASHIER_BRANCH_ID),
                )
            },
            "label": "Dev Admin Key",
        },
        {
            "api_key": DEV_CASHIER_API_KEY,
            "actor_id": _DEV_CASHIER_ACTOR_ID,
            "actor_type": "USER",
            "allowed_business_ids": (str(DEV_BUSINESS_ID),),
            "allowed_branch_ids_by_business": {
                str(DEV_BUSINESS_ID): (str(DEV_CASHIER_BRANCH_ID),)
            },
            "label": "Dev Cashier Key",
        },
    )

    for spec in credential_specs:
        existing = ApiKeyService.find_by_reference(
            key_hash=hash_api_key(spec["api_key"])
        )
        if existing is not None:
            continue
        ApiKeyService.create_api_key_credential(
            api_key=spec["api_key"],
            actor_id=spec["actor_id"],
            actor_type=spec["actor_type"],
            allowed_business_ids=spec["allowed_business_ids"],
            allowed_branch_ids_by_business=spec["allowed_branch_ids_by_business"],
            created_by_actor_id="system.bootstrap",
            label=spec["label"],
        )


def _build_auth_provider() -> DbAuthProvider:
    return DbAuthProvider()


def _build_event_factory():
    def _event_factory(*, command, event_type: str, payload: dict) -> dict[str, Any]:
        return {
            "event_id": command.command_id,
            "event_type": event_type,
            "event_version": 1,
            "business_id": command.business_id,
            "branch_id": command.branch_id,
            "source_engine": command.source_engine,
            "actor_type": command.actor_type,
            "actor_id": command.actor_id,
            "correlation_id": command.correlation_id,
            "causation_id": None,
            "payload": dict(payload),
            "reference": {},
            "created_at": command.issued_at,
            "status": "FINAL",
            "correction_of": None,
        }

    return _event_factory


def _build_default_numbering_provider(business_id: uuid.UUID) -> InMemoryNumberingProvider:
    """
    Register default sequential numbering policies for all document types.
    Each business production deployment should override these with DB-backed policies.
    """
    provider = InMemoryNumberingProvider()
    bid = str(business_id)
    default_policies = [
        ("RECEIPT",                 "RCP-",  "YEARLY"),
        ("INVOICE",                 "INV-",  "YEARLY"),
        ("QUOTE",                   "QT-",   "YEARLY"),
        ("PROFORMA_INVOICE",        "PRO-",  "YEARLY"),
        ("CREDIT_NOTE",             "CN-",   "YEARLY"),
        ("DEBIT_NOTE",              "DBN-",  "YEARLY"),
        ("PURCHASE_ORDER",          "PO-",   "YEARLY"),
        ("GOODS_RECEIPT_NOTE",      "GRN-",  "YEARLY"),
        ("DELIVERY_NOTE",           "DN-",   "YEARLY"),
        ("SALES_ORDER",             "SO-",   "YEARLY"),
        ("REFUND_NOTE",             "REF-",  "YEARLY"),
        ("WORK_ORDER",              "WO-",   "YEARLY"),
        ("CUTTING_LIST",            "CL-",   "YEARLY"),
        ("COMPLETION_CERTIFICATE",  "CC-",   "YEARLY"),
        ("KITCHEN_ORDER_TICKET",    "KOT-",  "DAILY"),
        ("FOLIO",                   "FOL-",  "YEARLY"),
        ("RESERVATION_CONFIRMATION","RESV-", "YEARLY"),
        ("REGISTRATION_CARD",       "REG-",  "YEARLY"),
        ("CANCELLATION_NOTE",       "CXL-",  "YEARLY"),
        ("PAYMENT_VOUCHER",         "PV-",   "YEARLY"),
        ("PETTY_CASH_VOUCHER",      "PCV-",  "MONTHLY"),
        ("STOCK_TRANSFER_NOTE",     "STN-",  "MONTHLY"),
        ("STOCK_ADJUSTMENT_NOTE",   "SAN-",  "MONTHLY"),
        ("STATEMENT",               "STMT-", "MONTHLY"),
        ("CASH_SESSION_RECONCILIATION", "CSR-", "DAILY"),
        ("MATERIAL_REQUISITION",    "MRN-",  "MONTHLY"),
        ("JOB_SHEET",               "JS-",   "YEARLY"),
    ]
    for doc_type, prefix, reset_period in default_policies:
        policy_id = f"default-{doc_type.lower().replace('_', '-')}"
        provider.register_policy(NumberingPolicy(
            policy_id=policy_id,
            business_id_str=bid,
            doc_type=doc_type,
            prefix=prefix,
            padding=5,
            reset_period=reset_period,
        ))
    return provider


def _create_dependencies() -> HttpApiDependencies:
    _ensure_dev_identity_records()
    _ensure_dev_api_key_credentials()

    admin_projection_store = AdminProjectionStore()
    _rebuild_admin_projection_store_from_events(
        admin_projection_store,
        DEV_BUSINESS_ID,
    )
    repository = AdminRepository(admin_projection_store)
    document_issuance_projection_store = DocumentIssuanceProjectionStore()
    _rebuild_document_issuance_projection_store_from_events(
        document_issuance_projection_store,
        DEV_BUSINESS_ID,
    )
    document_issuance_repository = DocumentIssuanceRepository(
        document_issuance_projection_store
    )

    business_context = _build_business_context()
    permission_provider = _build_permission_provider()
    feature_flag_provider = RepositoryFeatureFlagProvider(repository)
    compliance_provider = RepositoryComplianceProvider(repository)
    document_provider = RepositoryDocumentProvider(repository)

    # --- Event subscriber registry ---
    # Populated below via wire_all_subscriptions().
    # Captured by _subscribed_persist_event so all services share one registry.
    subscriber_registry = SubscriberRegistry()

    def _subscribed_persist_event(event_data, context, registry, **kwargs):
        """Thin wrapper that always passes subscriber_registry to persist_event."""
        return persist_event(
            event_data, context, registry,
            subscriber_registry=subscriber_registry,
            **kwargs,
        )

    dispatcher = CommandDispatcher(
        context=business_context,
        permission_provider=permission_provider,
        feature_flag_provider=feature_flag_provider,
        compliance_provider=compliance_provider,
        document_provider=document_provider,
    )
    event_type_registry = EventTypeRegistry()
    event_factory = _build_event_factory()
    command_bus = CommandBus(
        dispatcher=dispatcher,
        persist_event=_subscribed_persist_event,
        context=business_context,
        event_type_registry=event_type_registry,
    )
    admin_service = AdminDataService(
        business_context=business_context,
        dispatcher=dispatcher,
        command_bus=command_bus,
        event_factory=event_factory,
        persist_event=_subscribed_persist_event,
        event_type_registry=event_type_registry,
        projection_store=admin_projection_store,
    )
    numbering_provider = _build_default_numbering_provider(DEV_BUSINESS_ID)
    document_issuance_service = DocumentIssuanceService(
        business_context=business_context,
        dispatcher=dispatcher,
        command_bus=command_bus,
        event_factory=event_factory,
        persist_event=_subscribed_persist_event,
        event_type_registry=event_type_registry,
        projection_store=document_issuance_projection_store,
        document_provider=document_provider,
        numbering_provider=numbering_provider,
    )

    # Build resolvers that enrich auto-generated documents with issuer and
    # customer details. Business name comes from the identity store Django ORM.
    # Customer name will be extended once a persistent customer profile DB exists.
    def _business_info_resolver(business_id: str) -> dict:
        try:
            biz = _BusinessModel.objects.filter(business_id=business_id).first()
            if biz:
                return {
                    "business_name":    biz.name,
                    "default_currency": biz.default_currency,
                    "business_address": biz.address,
                    "business_city":    biz.city,
                    "country_code":     biz.country_code,
                    "business_phone":   biz.phone,
                    "business_email":   biz.email,
                    "tax_id":           biz.tax_id,
                    "logo_url":         biz.logo_url,
                }
        except Exception:
            pass
        return {}

    def _customer_info_resolver(customer_id: str | None) -> dict:
        if not customer_id:
            return {"customer_name": "Walk-in Customer"}
        # Persistent customer profile DB not yet implemented.
        # Returns minimal dict; extend when CustomerProfileService is available.
        return {"customer_name": "Customer", "customer_id": str(customer_id)}

    # Wire document subscription handler into the shared subscriber registry.
    # When engine events fire (e.g. retail.sale.completed.v1), the handler
    # will automatically issue the appropriate documents.
    wire_all_subscriptions(
        subscriber_registry,
        document_service=document_issuance_service,
        business_info_resolver=_business_info_resolver,
        customer_info_resolver=_customer_info_resolver,
    )

    return HttpApiDependencies(
        admin_service=admin_service,
        admin_repository=repository,
        id_provider=UuidIdProvider(),
        clock=UtcClock(),
        auth_provider=_build_auth_provider(),
        permission_provider=permission_provider,
        document_issuance_service=document_issuance_service,
        document_issuance_repository=document_issuance_repository,
    )


def build_dependencies() -> HttpApiDependencies:
    """
    Lazy singleton wiring for adapter runtime.
    """
    global _DEPENDENCIES
    with _DEPENDENCIES_LOCK:
        if _DEPENDENCIES is None:
            _DEPENDENCIES = _create_dependencies()
        return _DEPENDENCIES
