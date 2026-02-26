"""
BOS QR Menu Engine — Events, Commands, Service, Policies
=========================================================
Restaurant-specific. Static QR per table/room → CartSession token (expires) →
Customer self-orders → PENDING_CONFIRM → Staff accept/reject → Restaurant workflow.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.commands.rejection import RejectionReason

# ── Event Types ───────────────────────────────────────────────

QR_MENU_REGISTERED_V1 = "qr_menu.registered.v1"
QR_MENU_SESSION_CREATED_V1 = "qr_menu.session.created.v1"
QR_MENU_ITEM_ORDERED_V1 = "qr_menu.item.ordered.v1"
QR_MENU_ITEM_REMOVED_V1 = "qr_menu.item.removed.v1"
QR_MENU_ORDER_SUBMITTED_V1 = "qr_menu.order.submitted.v1"
QR_MENU_ORDER_ACCEPTED_V1 = "qr_menu.order.accepted.v1"
QR_MENU_ORDER_REJECTED_V1 = "qr_menu.order.rejected.v1"
QR_MENU_CLARIFICATION_REQUESTED_V1 = "qr_menu.order.clarification_requested.v1"
QR_MENU_SESSION_EXPIRED_V1 = "qr_menu.session.expired.v1"

ALL_EVENT_TYPES = (
    QR_MENU_REGISTERED_V1, QR_MENU_SESSION_CREATED_V1,
    QR_MENU_ITEM_ORDERED_V1, QR_MENU_ITEM_REMOVED_V1,
    QR_MENU_ORDER_SUBMITTED_V1, QR_MENU_ORDER_ACCEPTED_V1,
    QR_MENU_ORDER_REJECTED_V1, QR_MENU_CLARIFICATION_REQUESTED_V1,
    QR_MENU_SESSION_EXPIRED_V1,
)

SESSION_ACTIVE = "ACTIVE"
SESSION_PENDING_CONFIRM = "PENDING_CONFIRM"
SESSION_ACCEPTED = "ACCEPTED"
SESSION_REJECTED = "REJECTED"
SESSION_EXPIRED = "EXPIRED"

PLACE_TABLE = "TABLE"
PLACE_ROOM = "ROOM"
PLACE_COUNTER = "COUNTER"
VALID_PLACE_TYPES = frozenset({PLACE_TABLE, PLACE_ROOM, PLACE_COUNTER})

SCOPE_BRANCH_REQUIRED = "BRANCH_REQUIRED"
ACTOR_REQUIRED = "ACTOR_REQUIRED"

COMMAND_TO_EVENT_TYPE = {
    "qr_menu.register.request": QR_MENU_REGISTERED_V1,
    "qr_menu.session.create.request": QR_MENU_SESSION_CREATED_V1,
    "qr_menu.item.order.request": QR_MENU_ITEM_ORDERED_V1,
    "qr_menu.item.remove.request": QR_MENU_ITEM_REMOVED_V1,
    "qr_menu.order.submit.request": QR_MENU_ORDER_SUBMITTED_V1,
    "qr_menu.order.accept.request": QR_MENU_ORDER_ACCEPTED_V1,
    "qr_menu.order.reject.request": QR_MENU_ORDER_REJECTED_V1,
    "qr_menu.order.clarify.request": QR_MENU_CLARIFICATION_REQUESTED_V1,
    "qr_menu.session.expire.request": QR_MENU_SESSION_EXPIRED_V1,
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
    "qr_menu.register.request": lambda cmd: {**_base(cmd),
        "place_qr_id": cmd.payload["place_qr_id"],
        "place_type": cmd.payload["place_type"],
        "place_label": cmd.payload["place_label"],
        "registered_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
    "qr_menu.session.create.request": lambda cmd: {**_base(cmd),
        "session_id": cmd.payload["session_id"],
        "place_qr_id": cmd.payload["place_qr_id"],
        "session_token": cmd.payload["session_token"],
        "expires_at": cmd.payload["expires_at"],
        "created_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
    "qr_menu.item.order.request": lambda cmd: {**_base(cmd),
        "session_id": cmd.payload["session_id"],
        "order_line_id": cmd.payload["order_line_id"],
        "item_id": cmd.payload["item_id"],
        "item_name": cmd.payload["item_name"],
        "quantity": cmd.payload["quantity"],
        "unit_price": cmd.payload["unit_price"],
        "notes": cmd.payload.get("notes", ""),
        "ordered_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
    "qr_menu.item.remove.request": lambda cmd: {**_base(cmd),
        "session_id": cmd.payload["session_id"],
        "order_line_id": cmd.payload["order_line_id"],
    },
    "qr_menu.order.submit.request": lambda cmd: {**_base(cmd),
        "session_id": cmd.payload["session_id"],
        "submitted_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
    "qr_menu.order.accept.request": lambda cmd: {**_base(cmd),
        "session_id": cmd.payload["session_id"],
        "restaurant_order_id": cmd.payload["restaurant_order_id"],
        "accepted_by": cmd.payload.get("accepted_by", ""),
        "accepted_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
    "qr_menu.order.reject.request": lambda cmd: {**_base(cmd),
        "session_id": cmd.payload["session_id"],
        "reason": cmd.payload.get("reason", ""),
        "rejected_by": cmd.payload.get("rejected_by", ""),
        "rejected_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
    "qr_menu.order.clarify.request": lambda cmd: {**_base(cmd),
        "session_id": cmd.payload["session_id"],
        "message": cmd.payload.get("message", ""),
        "requested_by": cmd.payload.get("requested_by", ""),
        "requested_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
    "qr_menu.session.expire.request": lambda cmd: {**_base(cmd),
        "session_id": cmd.payload["session_id"],
        "expired_at": cmd.payload.get("issued_at") or str(cmd.issued_at),
    },
}


def register_qr_menu_event_types(registry):
    for et in ALL_EVENT_TYPES:
        registry.register(et, lambda d: d)


# ── Commands ──────────────────────────────────────────────────

@dataclass(frozen=True)
class RegisterQRMenuRequest:
    """Register a static QR for a table, room, or counter."""
    business_id: uuid.UUID
    branch_id: uuid.UUID
    place_qr_id: str
    place_type: str
    place_label: str
    actor_id: str
    issued_at: datetime
    source_engine: str = "qr_menu"

    def __post_init__(self):
        if not isinstance(self.business_id, uuid.UUID):
            raise ValueError("business_id must be UUID.")
        if not isinstance(self.branch_id, uuid.UUID):
            raise ValueError("branch_id must be UUID.")
        if not self.place_qr_id:
            raise ValueError("place_qr_id must be non-empty.")
        if self.place_type not in VALID_PLACE_TYPES:
            raise ValueError(f"Invalid place_type: {self.place_type}")
        if not self.place_label:
            raise ValueError("place_label must be non-empty.")

    def to_command(self) -> dict:
        return {
            "command_type": "qr_menu.register.request",
            "business_id": self.business_id,
            "branch_id": self.branch_id,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BRANCH_REQUIRED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "place_qr_id": self.place_qr_id,
                "place_type": self.place_type,
                "place_label": self.place_label,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class CreateSessionRequest:
    """Create a session token when customer scans QR (expires)."""
    business_id: uuid.UUID
    branch_id: uuid.UUID
    session_id: str
    place_qr_id: str
    session_token: str
    expires_at: str
    actor_id: str
    issued_at: datetime
    source_engine: str = "qr_menu"

    def __post_init__(self):
        if not self.session_id:
            raise ValueError("session_id must be non-empty.")
        if not self.place_qr_id:
            raise ValueError("place_qr_id must be non-empty.")
        if not self.session_token:
            raise ValueError("session_token must be non-empty.")
        if not self.expires_at:
            raise ValueError("expires_at must be set.")

    def to_command(self) -> dict:
        return {
            "command_type": "qr_menu.session.create.request",
            "business_id": self.business_id,
            "branch_id": self.branch_id,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BRANCH_REQUIRED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "session_id": self.session_id,
                "place_qr_id": self.place_qr_id,
                "session_token": self.session_token,
                "expires_at": self.expires_at,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class OrderItemRequest:
    """Customer orders an item from QR Menu."""
    business_id: uuid.UUID
    branch_id: uuid.UUID
    session_id: str
    order_line_id: str
    item_id: str
    item_name: str
    quantity: int
    unit_price: int
    actor_id: str
    issued_at: datetime
    notes: str = ""
    source_engine: str = "qr_menu"

    def __post_init__(self):
        if not self.session_id:
            raise ValueError("session_id must be non-empty.")
        if not self.item_id:
            raise ValueError("item_id must be non-empty.")
        if self.quantity <= 0:
            raise ValueError("quantity must be > 0.")
        if self.unit_price < 0:
            raise ValueError("unit_price must be >= 0.")

    def to_command(self) -> dict:
        return {
            "command_type": "qr_menu.item.order.request",
            "business_id": self.business_id,
            "branch_id": self.branch_id,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BRANCH_REQUIRED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "session_id": self.session_id,
                "order_line_id": self.order_line_id,
                "item_id": self.item_id,
                "item_name": self.item_name,
                "quantity": self.quantity,
                "unit_price": self.unit_price,
                "notes": self.notes,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class SubmitOrderRequest:
    """Customer submits order → PENDING_CONFIRM state."""
    business_id: uuid.UUID
    branch_id: uuid.UUID
    session_id: str
    actor_id: str
    issued_at: datetime
    source_engine: str = "qr_menu"

    def __post_init__(self):
        if not self.session_id:
            raise ValueError("session_id must be non-empty.")

    def to_command(self) -> dict:
        return {
            "command_type": "qr_menu.order.submit.request",
            "business_id": self.business_id,
            "branch_id": self.branch_id,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BRANCH_REQUIRED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "session_id": self.session_id,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class AcceptQROrderRequest:
    """Staff accepts order → links to restaurant_order_id."""
    business_id: uuid.UUID
    branch_id: uuid.UUID
    session_id: str
    restaurant_order_id: str
    actor_id: str
    issued_at: datetime
    source_engine: str = "qr_menu"

    def __post_init__(self):
        if not self.session_id:
            raise ValueError("session_id must be non-empty.")
        if not self.restaurant_order_id:
            raise ValueError("restaurant_order_id must be non-empty.")

    def to_command(self) -> dict:
        return {
            "command_type": "qr_menu.order.accept.request",
            "business_id": self.business_id,
            "branch_id": self.branch_id,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BRANCH_REQUIRED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "session_id": self.session_id,
                "restaurant_order_id": self.restaurant_order_id,
                "accepted_by": self.actor_id,
                "issued_at": str(self.issued_at),
            },
        }


@dataclass(frozen=True)
class RejectQROrderRequest:
    """Staff rejects the QR order."""
    business_id: uuid.UUID
    branch_id: uuid.UUID
    session_id: str
    reason: str
    actor_id: str
    issued_at: datetime
    source_engine: str = "qr_menu"

    def __post_init__(self):
        if not self.session_id:
            raise ValueError("session_id must be non-empty.")

    def to_command(self) -> dict:
        return {
            "command_type": "qr_menu.order.reject.request",
            "business_id": self.business_id,
            "branch_id": self.branch_id,
            "source_engine": self.source_engine,
            "actor_id": self.actor_id,
            "issued_at": self.issued_at,
            "scope_requirement": SCOPE_BRANCH_REQUIRED,
            "actor_requirement": ACTOR_REQUIRED,
            "payload": {
                "session_id": self.session_id,
                "reason": self.reason,
                "rejected_by": self.actor_id,
                "issued_at": str(self.issued_at),
            },
        }


# ── Projection Store ──────────────────────────────────────────

class QRMenuProjectionStore:
    def __init__(self):
        self._events: List[dict] = []
        self._places: Dict[str, dict] = {}
        self._sessions: Dict[str, dict] = {}

    def apply(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        if event_type == QR_MENU_REGISTERED_V1:
            pid = payload["place_qr_id"]
            self._places[pid] = {
                "place_qr_id": pid,
                "place_type": payload["place_type"],
                "place_label": payload["place_label"],
                "business_id": payload["business_id"],
                "branch_id": payload["branch_id"],
            }
        elif event_type == QR_MENU_SESSION_CREATED_V1:
            sid = payload["session_id"]
            self._sessions[sid] = {
                "session_id": sid,
                "place_qr_id": payload["place_qr_id"],
                "session_token": payload["session_token"],
                "expires_at": payload["expires_at"],
                "status": SESSION_ACTIVE,
                "order_lines": [],
                "restaurant_order_id": None,
            }
        elif event_type == QR_MENU_ITEM_ORDERED_V1:
            sess = self._sessions.get(payload["session_id"])
            if sess:
                sess["order_lines"].append({
                    "order_line_id": payload["order_line_id"],
                    "item_id": payload["item_id"],
                    "item_name": payload["item_name"],
                    "quantity": payload["quantity"],
                    "unit_price": payload["unit_price"],
                    "notes": payload.get("notes", ""),
                })
        elif event_type == QR_MENU_ITEM_REMOVED_V1:
            sess = self._sessions.get(payload["session_id"])
            if sess:
                sess["order_lines"] = [
                    l for l in sess["order_lines"]
                    if l["order_line_id"] != payload["order_line_id"]
                ]
        elif event_type == QR_MENU_ORDER_SUBMITTED_V1:
            sess = self._sessions.get(payload["session_id"])
            if sess:
                sess["status"] = SESSION_PENDING_CONFIRM
        elif event_type == QR_MENU_ORDER_ACCEPTED_V1:
            sess = self._sessions.get(payload["session_id"])
            if sess:
                sess["status"] = SESSION_ACCEPTED
                sess["restaurant_order_id"] = payload["restaurant_order_id"]
        elif event_type == QR_MENU_ORDER_REJECTED_V1:
            sess = self._sessions.get(payload["session_id"])
            if sess:
                sess["status"] = SESSION_REJECTED
        elif event_type == QR_MENU_SESSION_EXPIRED_V1:
            sess = self._sessions.get(payload["session_id"])
            if sess:
                sess["status"] = SESSION_EXPIRED

    def get_place(self, place_qr_id: str) -> Optional[dict]:
        return self._places.get(place_qr_id)

    def get_session(self, session_id: str) -> Optional[dict]:
        return self._sessions.get(session_id)

    def get_pending_sessions(self) -> List[dict]:
        return [s for s in self._sessions.values() if s["status"] == SESSION_PENDING_CONFIRM]

    @property
    def event_count(self) -> int:
        return len(self._events)

    def truncate(self):
        self._events.clear()
        self._places.clear()
        self._sessions.clear()


# ── Policies ──────────────────────────────────────────────────

def session_must_be_active_policy(command, session_lookup=None) -> Optional[RejectionReason]:
    if session_lookup is None:
        return None
    sid = command.payload.get("session_id")
    if sid:
        sess = session_lookup(sid)
        if sess is None:
            return RejectionReason(
                code="SESSION_NOT_FOUND",
                message=f"QR Menu session '{sid}' not found.",
                policy_name="session_must_be_active_policy",
            )
        if sess["status"] != SESSION_ACTIVE:
            return RejectionReason(
                code="SESSION_NOT_ACTIVE",
                message=f"Session is '{sess['status']}', expected ACTIVE.",
                policy_name="session_must_be_active_policy",
            )
    return None


def session_must_be_pending_confirm_policy(command, session_lookup=None) -> Optional[RejectionReason]:
    if session_lookup is None:
        return None
    sid = command.payload.get("session_id")
    if sid:
        sess = session_lookup(sid)
        if sess is None:
            return RejectionReason(
                code="SESSION_NOT_FOUND",
                message=f"QR Menu session '{sid}' not found.",
                policy_name="session_must_be_pending_confirm_policy",
            )
        if sess["status"] != SESSION_PENDING_CONFIRM:
            return RejectionReason(
                code="SESSION_NOT_PENDING",
                message=f"Session is '{sess['status']}', expected PENDING_CONFIRM.",
                policy_name="session_must_be_pending_confirm_policy",
            )
    return None


def session_must_have_items_policy(command, session_lookup=None) -> Optional[RejectionReason]:
    if session_lookup is None:
        return None
    sid = command.payload.get("session_id")
    if sid:
        sess = session_lookup(sid)
        if sess and not sess.get("order_lines"):
            return RejectionReason(
                code="SESSION_EMPTY",
                message="Cannot submit an order with no items.",
                policy_name="session_must_have_items_policy",
            )
    return None


# ── Service ───────────────────────────────────────────────────

class QRMenuService:
    def __init__(self, *, event_factory, persist_event, event_type_registry,
                 projection_store: QRMenuProjectionStore, feature_flag_evaluator=None):
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
