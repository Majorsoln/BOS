"""
BOS Cart QR Engine — Events, Commands, Service, Policies
=========================================================
Cashier creates a product range QR/link → Customer selects → Cashier loads to POS.
Security: configurable expiry, single/multi-use, explicit cashier transfer step.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.commands.rejection import RejectionReason

# ── Event Types ───────────────────────────────────────────────

CART_QR_CREATED_V1 = "cart_qr.created.v1"
CART_QR_ITEM_ADDED_V1 = "cart_qr.item_added.v1"
CART_QR_ITEM_REMOVED_V1 = "cart_qr.item_removed.v1"
CART_QR_PUBLISHED_V1 = "cart_qr.published.v1"
CART_QR_SELECTION_RECEIVED_V1 = "cart_qr.selection_received.v1"
CART_QR_TRANSFERRED_TO_POS_V1 = "cart_qr.transferred_to_pos.v1"
CART_QR_EXPIRED_V1 = "cart_qr.expired.v1"
CART_QR_CANCELLED_V1 = "cart_qr.cancelled.v1"

ALL_EVENT_TYPES = (
    CART_QR_CREATED_V1, CART_QR_ITEM_ADDED_V1, CART_QR_ITEM_REMOVED_V1,
    CART_QR_PUBLISHED_V1, CART_QR_SELECTION_RECEIVED_V1,
    CART_QR_TRANSFERRED_TO_POS_V1, CART_QR_EXPIRED_V1, CART_QR_CANCELLED_V1,
)

STATUS_DRAFT = "DRAFT"
STATUS_PUBLISHED = "PUBLISHED"
STATUS_SELECTION_RECEIVED = "SELECTION_RECEIVED"
STATUS_TRANSFERRED = "TRANSFERRED"
STATUS_EXPIRED = "EXPIRED"
STATUS_CANCELLED = "CANCELLED"

USAGE_SINGLE = "SINGLE_USE"
USAGE_MULTI = "MULTI_USE"
VALID_USAGE_MODES = frozenset({USAGE_SINGLE, USAGE_MULTI})

SCOPE_BRANCH_REQUIRED = "BRANCH_REQUIRED"
ACTOR_REQUIRED = "ACTOR_REQUIRED"

COMMAND_TO_EVENT_TYPE = {
    "cart_qr.create.request": CART_QR_CREATED_V1,
    "cart_qr.item.add.request": CART_QR_ITEM_ADDED_V1,
    "cart_qr.item.remove.request": CART_QR_ITEM_REMOVED_V1,
    "cart_qr.publish.request": CART_QR_PUBLISHED_V1,
    "cart_qr.selection.receive.request": CART_QR_SELECTION_RECEIVED_V1,
    "cart_qr.transfer_to_pos.request": CART_QR_TRANSFERRED_TO_POS_V1,
    "cart_qr.expire.request": CART_QR_EXPIRED_V1,
    "cart_qr.cancel.request": CART_QR_CANCELLED_V1,
}


def _base(cmd):
    return {
        "business_id": str(cmd.business_id),
        "branch_id": str(cmd.branch_id) if getattr(cmd, "branch_id", None) else None,
        "actor_id": getattr(cmd, "actor_id", None),
        "correlation_id": str(cmd.correlation_id) if hasattr(cmd, "correlation_id") else None,
        "command_id": str(cmd.command_id) if hasattr(cmd, "command_id") else None,
    }


PAYLOAD_BUILDERS = {
    "cart_qr.create.request": lambda cmd: {**_base(cmd),
        "cart_qr_id": cmd.payload["cart_qr_id"],
        "usage_mode": cmd.payload.get("usage_mode", USAGE_SINGLE),
        "expiry_hours": cmd.payload.get("expiry_hours", 24),
        "created_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
    "cart_qr.item.add.request": lambda cmd: {**_base(cmd),
        "cart_qr_id": cmd.payload["cart_qr_id"],
        "item_id": cmd.payload["item_id"],
        "sku": cmd.payload["sku"],
        "item_name": cmd.payload["item_name"],
        "unit_price": cmd.payload["unit_price"],
        "max_quantity": cmd.payload.get("max_quantity", 999),
        "image_url": cmd.payload.get("image_url"),
    },
    "cart_qr.item.remove.request": lambda cmd: {**_base(cmd),
        "cart_qr_id": cmd.payload["cart_qr_id"],
        "item_id": cmd.payload["item_id"],
    },
    "cart_qr.publish.request": lambda cmd: {**_base(cmd),
        "cart_qr_id": cmd.payload["cart_qr_id"],
        "qr_token": cmd.payload["qr_token"],
        "expires_at": cmd.payload["expires_at"],
        "published_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
    "cart_qr.selection.receive.request": lambda cmd: {**_base(cmd),
        "cart_qr_id": cmd.payload["cart_qr_id"],
        "selected_items": cmd.payload["selected_items"],
        "received_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
    "cart_qr.transfer_to_pos.request": lambda cmd: {**_base(cmd),
        "cart_qr_id": cmd.payload["cart_qr_id"],
        "pos_sale_id": cmd.payload["pos_sale_id"],
        "transferred_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
    "cart_qr.expire.request": lambda cmd: {**_base(cmd),
        "cart_qr_id": cmd.payload["cart_qr_id"],
        "expired_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
    "cart_qr.cancel.request": lambda cmd: {**_base(cmd),
        "cart_qr_id": cmd.payload["cart_qr_id"],
        "reason": cmd.payload.get("reason", ""),
        "cancelled_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
}


def register_cart_qr_event_types(registry):
    for et in ALL_EVENT_TYPES:
        registry.register(et, lambda d: d)


# ── Commands ──────────────────────────────────────────────────

@dataclass(frozen=True)
class CreateCartQRRequest:
    business_id: uuid.UUID
    branch_id: uuid.UUID
    cart_qr_id: str
    actor_id: str
    issued_at: datetime
    usage_mode: str = USAGE_SINGLE
    expiry_hours: int = 24
    source_engine: str = "cart_qr"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID.")
        if not self.cart_qr_id:
            raise ValueError("cart_qr_id must be non-empty.")
        if self.usage_mode not in VALID_USAGE_MODES:
            raise ValueError(f"Invalid usage_mode: {self.usage_mode}")
        if self.expiry_hours <= 0:
            raise ValueError("expiry_hours must be > 0.")

    def to_command(self) -> dict:
        return {
            "command_type": "cart_qr.create.request",
            "business_id": self.business_id,
            "branch_id": self.branch_id,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BRANCH_REQUIRED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "cart_qr_id": self.cart_qr_id,
                "usage_mode": self.usage_mode,
                "expiry_hours": self.expiry_hours,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class AddItemToCartQRRequest:
    business_id: uuid.UUID
    branch_id: uuid.UUID
    cart_qr_id: str
    item_id: str
    sku: str
    item_name: str
    unit_price: int
    actor_id: str
    issued_at: datetime
    max_quantity: int = 999
    image_url: Optional[str] = None
    source_engine: str = "cart_qr"

    def __post_init__(self):
        if not self.cart_qr_id:
            raise ValueError("cart_qr_id must be non-empty.")
        if not self.item_id:
            raise ValueError("item_id must be non-empty.")
        if self.unit_price <= 0:
            raise ValueError("unit_price must be > 0.")

    def to_command(self) -> dict:
        return {
            "command_type": "cart_qr.item.add.request",
            "business_id": self.business_id,
            "branch_id": self.branch_id,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BRANCH_REQUIRED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "cart_qr_id": self.cart_qr_id,
                "item_id": self.item_id,
                "sku": self.sku,
                "item_name": self.item_name,
                "unit_price": self.unit_price,
                "max_quantity": self.max_quantity,
                "image_url": self.image_url,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class PublishCartQRRequest:
    business_id: uuid.UUID
    branch_id: uuid.UUID
    cart_qr_id: str
    qr_token: str
    expires_at: str
    actor_id: str
    issued_at: datetime
    source_engine: str = "cart_qr"

    def __post_init__(self):
        if not self.cart_qr_id:
            raise ValueError("cart_qr_id must be non-empty.")
        if not self.qr_token:
            raise ValueError("qr_token must be non-empty.")
        if not self.expires_at:
            raise ValueError("expires_at must be set.")

    def to_command(self) -> dict:
        return {
            "command_type": "cart_qr.publish.request",
            "business_id": self.business_id,
            "branch_id": self.branch_id,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BRANCH_REQUIRED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "cart_qr_id": self.cart_qr_id,
                "qr_token": self.qr_token,
                "expires_at": self.expires_at,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class ReceiveSelectionRequest:
    business_id: uuid.UUID
    branch_id: uuid.UUID
    cart_qr_id: str
    selected_items: Tuple[dict, ...]
    actor_id: str
    issued_at: datetime
    source_engine: str = "cart_qr"

    def __post_init__(self):
        if not self.cart_qr_id:
            raise ValueError("cart_qr_id must be non-empty.")
        if not self.selected_items:
            raise ValueError("selected_items must be non-empty.")

    def to_command(self) -> dict:
        return {
            "command_type": "cart_qr.selection.receive.request",
            "business_id": self.business_id,
            "branch_id": self.branch_id,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BRANCH_REQUIRED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "cart_qr_id": self.cart_qr_id,
                "selected_items": [dict(i) for i in self.selected_items],
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class TransferToPOSRequest:
    business_id: uuid.UUID
    branch_id: uuid.UUID
    cart_qr_id: str
    pos_sale_id: str
    actor_id: str
    issued_at: datetime
    source_engine: str = "cart_qr"

    def __post_init__(self):
        if not self.cart_qr_id:
            raise ValueError("cart_qr_id must be non-empty.")
        if not self.pos_sale_id:
            raise ValueError("pos_sale_id must be non-empty.")

    def to_command(self) -> dict:
        return {
            "command_type": "cart_qr.transfer_to_pos.request",
            "business_id": self.business_id,
            "branch_id": self.branch_id,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BRANCH_REQUIRED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "cart_qr_id": self.cart_qr_id,
                "pos_sale_id": self.pos_sale_id,
                "issued_at": str(self.issued_at),
            },
        }


# ── Projection Store ──────────────────────────────────────────

class CartQRProjectionStore:
    def __init__(self):
        self._events: List[dict] = []
        self._carts: Dict[str, dict] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events.append({"event_type": event_type, "payload": payload})
        cid = payload.get("cart_qr_id")
        if not cid:
            return
        if event_type == CART_QR_CREATED_V1:
            self._carts[cid] = {
                "cart_qr_id": cid, "status": STATUS_DRAFT,
                "usage_mode": payload.get("usage_mode", USAGE_SINGLE),
                "expiry_hours": payload.get("expiry_hours", 24),
                "items": [], "qr_token": None, "expires_at": None,
                "selected_items": [], "pos_sale_id": None,
            }
        elif event_type == CART_QR_ITEM_ADDED_V1:
            cart = self._carts.get(cid)
            if cart:
                cart["items"].append({
                    "item_id": payload["item_id"], "sku": payload["sku"],
                    "item_name": payload["item_name"], "unit_price": payload["unit_price"],
                    "max_quantity": payload.get("max_quantity", 999),
                })
        elif event_type == CART_QR_ITEM_REMOVED_V1:
            cart = self._carts.get(cid)
            if cart:
                cart["items"] = [i for i in cart["items"] if i["item_id"] != payload["item_id"]]
        elif event_type == CART_QR_PUBLISHED_V1:
            cart = self._carts.get(cid)
            if cart:
                cart["status"] = STATUS_PUBLISHED
                cart["qr_token"] = payload["qr_token"]
                cart["expires_at"] = payload["expires_at"]
        elif event_type == CART_QR_SELECTION_RECEIVED_V1:
            cart = self._carts.get(cid)
            if cart:
                cart["status"] = STATUS_SELECTION_RECEIVED
                cart["selected_items"] = payload.get("selected_items", [])
        elif event_type == CART_QR_TRANSFERRED_TO_POS_V1:
            cart = self._carts.get(cid)
            if cart:
                cart["status"] = STATUS_TRANSFERRED
                cart["pos_sale_id"] = payload["pos_sale_id"]
        elif event_type == CART_QR_EXPIRED_V1:
            cart = self._carts.get(cid)
            if cart:
                cart["status"] = STATUS_EXPIRED
        elif event_type == CART_QR_CANCELLED_V1:
            cart = self._carts.get(cid)
            if cart:
                cart["status"] = STATUS_CANCELLED

    def get_cart(self, cart_qr_id: str) -> Optional[dict]:
        return self._carts.get(cart_qr_id)

    @property
    def event_count(self) -> int:
        return len(self._events)

    def truncate(self):
        self._events.clear()
        self._carts.clear()


# ── Policies ──────────────────────────────────────────────────

def cart_qr_must_be_draft_policy(command, cart_lookup=None) -> Optional[RejectionReason]:
    if cart_lookup is None:
        return None
    cid = command.payload.get("cart_qr_id")
    if cid:
        cart = cart_lookup(cid)
        if cart is None:
            return RejectionReason(
                code="CART_QR_NOT_FOUND",
                message=f"Cart QR '{cid}' not found.",
                policy_name="cart_qr_must_be_draft_policy",
            )
        if cart["status"] != STATUS_DRAFT:
            return RejectionReason(
                code="CART_QR_NOT_DRAFT",
                message=f"Cart QR is '{cart['status']}', expected DRAFT.",
                policy_name="cart_qr_must_be_draft_policy",
            )
    return None


def cart_qr_must_have_selection_policy(command, cart_lookup=None) -> Optional[RejectionReason]:
    if cart_lookup is None:
        return None
    cid = command.payload.get("cart_qr_id")
    if cid:
        cart = cart_lookup(cid)
        if cart is None:
            return RejectionReason(
                code="CART_QR_NOT_FOUND",
                message=f"Cart QR '{cid}' not found.",
                policy_name="cart_qr_must_have_selection_policy",
            )
        if cart["status"] != STATUS_SELECTION_RECEIVED:
            return RejectionReason(
                code="CART_QR_NO_SELECTION",
                message=f"Cart QR is '{cart['status']}', must be SELECTION_RECEIVED.",
                policy_name="cart_qr_must_have_selection_policy",
            )
    return None


# ── Service ───────────────────────────────────────────────────

class CartQRService:
    def __init__(self, *, event_factory, persist_event, event_type_registry,
                 projection_store: CartQRProjectionStore, feature_flag_evaluator=None):
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection = projection_store
        self._feature_flags = feature_flag_evaluator

    def _execute_command(self, command) -> dict:
        event_type = COMMAND_TO_EVENT_TYPE.get(command.command_type)
        if event_type is None:
            return {"rejected": RejectionReason(
                code="UNKNOWN_COMMAND",
                message=f"Unknown command: {command.command_type}",
                policy_name="_execute_command",
            )}
        builder = PAYLOAD_BUILDERS.get(command.command_type)
        if builder is None:
            return {"rejected": RejectionReason(
                code="NO_PAYLOAD_BUILDER",
                message=f"No builder for: {event_type}",
                policy_name="_execute_command",
            )}
        payload = builder(command)
        event_data = self._event_factory.create(
            event_type, payload, command.business_id,
            getattr(command, "branch_id", None),
        )
        self._persist_event(event_data)
        self._projection.apply(event_type, payload)
        return {"event_type": event_type, "payload": payload}
