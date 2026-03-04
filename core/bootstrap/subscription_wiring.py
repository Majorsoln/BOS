"""
BOS Bootstrap — Cross-Engine Subscription Wiring
==================================================
Wires all cross-engine subscription handlers to a SubscriberRegistry.

Call wire_all_subscriptions() during application startup with all
initialized engine services and the shared SubscriberRegistry.

This module is the ONLY place that instantiates subscription handlers
and registers them. Without calling this function, events emitted by
one engine will NOT reach subscriber handlers in other engines.

Pattern:
    1. Instantiate handler with its engine service
    2. For each (event_type, method_name) in engine's SUBSCRIPTIONS dict:
       a. Look up the method on the handler instance
       b. Register (event_type, handler_method, subscriber_engine)
          with the SubscriberRegistry

This module does NOT:
- Initialize services (services must be pre-built by the caller)
- Configure databases
- Register event types in the EventTypeRegistry
- Perform authentication or scope checks
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from core.events.registry import SubscriberRegistry

logger = logging.getLogger("bos.bootstrap")


def wire_all_subscriptions(
    subscriber_registry: SubscriberRegistry,
    *,
    cash_service: Optional[Any] = None,
    inventory_service: Optional[Any] = None,
    accounting_service: Optional[Any] = None,
    reporting_service: Optional[Any] = None,
    retail_service: Optional[Any] = None,
    document_service: Optional[Any] = None,
    business_info_resolver: Optional[Any] = None,
    customer_info_resolver: Optional[Any] = None,
) -> dict[str, int]:
    """
    Instantiate all subscription handlers and register them to the
    SubscriberRegistry.

    Args:
        subscriber_registry:     The SubscriberRegistry to register handlers into.
        cash_service:            Initialized CashService instance (optional).
        inventory_service:       Initialized InventoryService instance (optional).
        accounting_service:      Initialized AccountingService instance (optional).
        reporting_service:       Initialized ReportingService instance (optional).
        retail_service:          Initialized RetailService instance (optional).
        document_service:        Initialized DocumentIssuanceService instance (optional).
        business_info_resolver:  Optional callable(business_id: str) -> dict.
                                 Returns {business_name, business_address, tax_id, ...}.
                                 Injected into DocumentSubscriptionHandler to enrich
                                 all auto-issued documents with issuer details.
        customer_info_resolver:  Optional callable(customer_id: str | None) -> dict.
                                 Returns {customer_name, customer_address, ...}.
                                 Injected into DocumentSubscriptionHandler for
                                 customer-addressed documents.

    Returns:
        dict mapping engine name → number of subscriptions registered.

    Notes:
        - Services passed as None will result in that engine's handlers
          not being registered (safe — no handlers called for that engine).
        - This function is NOT idempotent. Calling it twice with the same
          registry and handler instances will raise DuplicateSubscriberError.
          Call once per application lifecycle.
    """
    registered: dict[str, int] = {}

    # ── Cash subscriptions ────────────────────────────────────────
    if cash_service is not None:
        from engines.cash.subscriptions import (
            CashSubscriptionHandler,
            CASH_SUBSCRIPTIONS,
        )
        cash_handler = CashSubscriptionHandler(cash_service=cash_service)
        count = _register_handlers(
            subscriber_registry=subscriber_registry,
            handler_instance=cash_handler,
            subscriptions=CASH_SUBSCRIPTIONS,
            subscriber_engine="cash",
        )
        registered["cash"] = count
        logger.info(f"Wired {count} cash subscription(s)")

    # ── Inventory subscriptions ───────────────────────────────────
    if inventory_service is not None:
        from engines.inventory.subscriptions import (
            InventorySubscriptionHandler,
            INVENTORY_SUBSCRIPTIONS,
        )
        inv_handler = InventorySubscriptionHandler(inventory_service=inventory_service)
        count = _register_handlers(
            subscriber_registry=subscriber_registry,
            handler_instance=inv_handler,
            subscriptions=INVENTORY_SUBSCRIPTIONS,
            subscriber_engine="inventory",
        )
        registered["inventory"] = count
        logger.info(f"Wired {count} inventory subscription(s)")

    # ── Accounting subscriptions ──────────────────────────────────
    if accounting_service is not None:
        from engines.accounting.subscriptions import (
            AccountingSubscriptionHandler,
            ACCOUNTING_SUBSCRIPTIONS,
        )
        acct_handler = AccountingSubscriptionHandler(accounting_service=accounting_service)
        count = _register_handlers(
            subscriber_registry=subscriber_registry,
            handler_instance=acct_handler,
            subscriptions=ACCOUNTING_SUBSCRIPTIONS,
            subscriber_engine="accounting",
        )
        registered["accounting"] = count
        logger.info(f"Wired {count} accounting subscription(s)")

    # ── Reporting subscriptions ───────────────────────────────────
    if reporting_service is not None:
        from engines.reporting.subscriptions import (
            ReportingSubscriptionHandler,
            SUBSCRIPTIONS as REPORTING_SUBSCRIPTIONS,
        )
        rep_handler = ReportingSubscriptionHandler(reporting_service=reporting_service)
        count = _register_handlers(
            subscriber_registry=subscriber_registry,
            handler_instance=rep_handler,
            subscriptions=REPORTING_SUBSCRIPTIONS,
            subscriber_engine="reporting",
        )
        registered["reporting"] = count
        logger.info(f"Wired {count} reporting subscription(s)")

    # ── Retail subscriptions ──────────────────────────────────────
    if retail_service is not None:
        from engines.retail.subscriptions import (
            RetailSubscriptionHandler,
            RETAIL_SUBSCRIPTIONS,
        )
        retail_handler = RetailSubscriptionHandler(retail_service=retail_service)
        count = _register_handlers(
            subscriber_registry=subscriber_registry,
            handler_instance=retail_handler,
            subscriptions=RETAIL_SUBSCRIPTIONS,
            subscriber_engine="retail",
        )
        registered["retail"] = count
        logger.info(f"Wired {count} retail subscription(s)")

    # ── Document subscriptions ────────────────────────────────────
    if document_service is not None:
        from engines.documents.subscriptions import (
            DocumentSubscriptionHandler,
            DOCUMENT_SUBSCRIPTIONS,
        )
        doc_handler = DocumentSubscriptionHandler(
            document_service=document_service,
            business_info_resolver=business_info_resolver,
            customer_info_resolver=customer_info_resolver,
        )
        count = _register_handlers(
            subscriber_registry=subscriber_registry,
            handler_instance=doc_handler,
            subscriptions=DOCUMENT_SUBSCRIPTIONS,
            subscriber_engine="documents",
        )
        registered["documents"] = count
        logger.info(f"Wired {count} document subscription(s)")

    total = sum(registered.values())
    logger.info(
        f"Subscription wiring complete: {total} total handler(s) registered "
        f"across {len(registered)} engine(s): {list(registered.keys())}"
    )
    return registered


def _register_handlers(
    subscriber_registry: SubscriberRegistry,
    handler_instance: Any,
    subscriptions: dict[str, str],
    subscriber_engine: str,
) -> int:
    """
    Register all handlers from a subscription dict onto the registry.

    Args:
        subscriber_registry: Registry to register into.
        handler_instance:    Handler object whose methods are called.
        subscriptions:       {event_type: method_name} dict.
        subscriber_engine:   Engine name for the handler.

    Returns:
        Number of handlers successfully registered.

    Skips entries where the method does not exist on the handler instance.
    """
    count = 0
    for event_type, method_name in subscriptions.items():
        handler_method = getattr(handler_instance, method_name, None)
        if handler_method is None:
            logger.warning(
                f"Subscription wiring: {subscriber_engine} handler has no "
                f"method '{method_name}' for event '{event_type}' — skipped"
            )
            continue
        subscriber_registry.register_subscriber(
            event_type=event_type,
            handler=handler_method,
            subscriber_engine=subscriber_engine,
        )
        count += 1
    return count
