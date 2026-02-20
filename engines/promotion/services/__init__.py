"""
BOS Promotion Engine — Application Service
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from core.commands.base import Command
from core.feature_flags.evaluator import FeatureFlagEvaluator
from engines.promotion.commands import PROMOTION_COMMAND_TYPES
from engines.promotion.events import (
    resolve_promotion_event_type, register_promotion_event_types,
    build_campaign_created_payload, build_campaign_activated_payload,
    build_campaign_deactivated_payload, build_coupon_issued_payload,
    build_coupon_redeemed_payload,
)

class EventFactoryProtocol(Protocol):
    def __call__(self, *, command: Command, event_type: str, payload: dict) -> dict: ...

class PersistEventProtocol(Protocol):
    def __call__(self, *, event_data: dict, context: Any, registry: Any, **kw) -> Any: ...


class PromotionProjectionStore:
    def __init__(self):
        self._events: List[dict] = []
        self._campaigns: Dict[str, dict] = {}
        self._coupons: Dict[str, dict] = {}
        self._total_discounts: int = 0

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})
        if event_type.startswith("promotion.campaign.created"):
            self._campaigns[payload["campaign_id"]] = {
                "status": "DRAFT", "name": payload["name"],
                "discount_type": payload["discount_type"],
                "discount_value": payload["discount_value"],
            }
        elif event_type.startswith("promotion.campaign.activated"):
            cid = payload["campaign_id"]
            if cid in self._campaigns:
                self._campaigns[cid]["status"] = "ACTIVE"
        elif event_type.startswith("promotion.campaign.deactivated"):
            cid = payload["campaign_id"]
            if cid in self._campaigns:
                self._campaigns[cid]["status"] = "INACTIVE"
        elif event_type.startswith("promotion.coupon.issued"):
            self._coupons[payload["coupon_id"]] = {
                "campaign_id": payload["campaign_id"],
                "status": "ISSUED",
            }
        elif event_type.startswith("promotion.coupon.redeemed"):
            cid = payload["coupon_id"]
            if cid in self._coupons:
                self._coupons[cid]["status"] = "REDEEMED"
                self._total_discounts += payload["discount_applied"]

    def get_campaign(self, campaign_id: str) -> Optional[dict]:
        return self._campaigns.get(campaign_id)

    def get_coupon(self, coupon_id: str) -> Optional[dict]:
        return self._coupons.get(coupon_id)

    @property
    def total_discounts(self) -> int:
        return self._total_discounts

    @property
    def event_count(self) -> int:
        return len(self._events)


PAYLOAD_BUILDERS = {
    "promotion.campaign.create.request": build_campaign_created_payload,
    "promotion.campaign.activate.request": build_campaign_activated_payload,
    "promotion.campaign.deactivate.request": build_campaign_deactivated_payload,
    "promotion.coupon.issue.request": build_coupon_issued_payload,
    "promotion.coupon.redeem.request": build_coupon_redeemed_payload,
}


@dataclass(frozen=True)
class PromotionExecutionResult:
    event_type: str
    event_data: dict
    persist_result: Any
    projection_applied: bool


class _PromotionCommandHandler:
    def __init__(self, service: "PromotionService"):
        self._service = service
    def execute(self, command: Command) -> PromotionExecutionResult:
        return self._service._execute_command(command)


class PromotionService:
    def __init__(self, *, business_context, command_bus,
                 event_factory: EventFactoryProtocol,
                 persist_event: PersistEventProtocol,
                 event_type_registry,
                 projection_store: PromotionProjectionStore | None = None,
                 feature_flag_provider=None):
        self._business_context = business_context
        self._command_bus = command_bus
        self._event_factory = event_factory
        self._persist_event = persist_event
        self._event_type_registry = event_type_registry
        self._projection_store = projection_store or PromotionProjectionStore()
        self._feature_flag_provider = feature_flag_provider
        register_promotion_event_types(self._event_type_registry)
        handler = _PromotionCommandHandler(self)
        for ct in sorted(PROMOTION_COMMAND_TYPES):
            self._command_bus.register_handler(ct, handler)

    def _is_persist_accepted(self, r: Any) -> bool:
        if hasattr(r, "accepted"):
            return bool(r.accepted)
        if isinstance(r, dict):
            return bool(r.get("accepted"))
        return bool(r)

    def _execute_command(self, command: Command) -> PromotionExecutionResult:
        ff = FeatureFlagEvaluator.evaluate(command, self._business_context, self._feature_flag_provider)
        if not ff.allowed:
            raise ValueError(f"Feature disabled: {ff.message}")

        event_type = resolve_promotion_event_type(command.command_type)
        if event_type is None:
            raise ValueError(f"Unsupported: {command.command_type}")
        builder = PAYLOAD_BUILDERS[command.command_type]
        payload = builder(command)
        event_data = self._event_factory(command=command, event_type=event_type, payload=payload)
        persist_result = self._persist_event(
            event_data=event_data, context=self._business_context,
            registry=self._event_type_registry, scope_requirement=command.scope_requirement)
        applied = False
        if self._is_persist_accepted(persist_result):
            self._projection_store.apply(event_type=event_type, payload=payload)
            applied = True
        return PromotionExecutionResult(
            event_type=event_type, event_data=event_data,
            persist_result=persist_result, projection_applied=applied)

    @property
    def projection_store(self) -> PromotionProjectionStore:
        return self._projection_store
