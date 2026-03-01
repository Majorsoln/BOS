"""
BOS Promotion Engine — Application Service
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from core.commands.base import Command
from core.context.scope_guard import enforce_scope_guard
from core.feature_flags.evaluator import FeatureFlagEvaluator
from engines.promotion.commands import PROMOTION_COMMAND_TYPES
from engines.promotion.events import (
    resolve_promotion_event_type, register_promotion_event_types,
    build_campaign_created_payload, build_campaign_activated_payload,
    build_campaign_deactivated_payload, build_coupon_issued_payload,
    build_coupon_redeemed_payload,
    # v2
    build_program_created_payload, build_program_activated_payload,
    build_program_deactivated_payload, build_rule_added_payload,
    build_evaluated_payload, build_applied_payload,
    build_credit_note_issued_payload, build_rebate_settled_payload,
    V2_PAYLOAD_BUILDERS,
    PROMOTION_PROGRAM_CREATED_V2, PROMOTION_PROGRAM_ACTIVATED_V2,
    PROMOTION_PROGRAM_DEACTIVATED_V2, PROMOTION_RULE_ADDED_V1,
    PROMOTION_EVALUATED_V1, PROMOTION_APPLIED_V1,
    PROMOTION_CREDIT_NOTE_ISSUED_V1, PROMOTION_REBATE_SETTLED_V1,
)

class EventFactoryProtocol(Protocol):
    def __call__(self, *, command: Command, event_type: str, payload: dict) -> dict: ...

class PersistEventProtocol(Protocol):
    def __call__(self, *, event_data: dict, context: Any, registry: Any, **kw) -> Any: ...


class PromotionProjectionStore:
    def __init__(self):
        self._events: List[dict] = []
        # v1
        self._campaigns: Dict[str, dict] = {}
        self._coupons: Dict[str, dict] = {}
        self._total_discounts: int = 0
        # v2
        self._programs: Dict[str, dict] = {}   # program_id → program record
        self._program_rules: Dict[str, List[dict]] = {}  # program_id → [rules]
        self._evaluations: Dict[str, dict] = {}  # evaluation_id → result
        self._applications: Dict[str, dict] = {}  # application_id → application

    def apply(self, event_type: str, payload: dict) -> None:
        self._events.append({"event_type": event_type, "payload": payload})

        # ── v1 ──────────────────────────────────────────────
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

        # ── v2 ──────────────────────────────────────────────
        elif event_type == PROMOTION_PROGRAM_CREATED_V2:
            pid = payload["program_id"]
            self._programs[pid] = {
                "program_id": pid,
                "name": payload["name"],
                "timing": payload["timing"],
                "tax_mode": payload["tax_mode"],
                "settlement": payload["settlement"],
                "stackability": payload["stackability"],
                "stack_tags": payload.get("stack_tags", []),
                "budget_ceiling": payload.get("budget_ceiling", 0),
                "usage_cap": payload.get("usage_cap", 0),
                "customer_cap": payload.get("customer_cap", 0),
                "scope": payload.get("scope", {}),
                "validity": payload.get("validity", {}),
                "status": "DRAFT",
                "usage_count": 0,
                "total_discount_issued": 0,
            }
            self._program_rules[pid] = []

        elif event_type == PROMOTION_PROGRAM_ACTIVATED_V2:
            pid = payload["program_id"]
            if pid in self._programs:
                self._programs[pid]["status"] = "ACTIVE"

        elif event_type == PROMOTION_PROGRAM_DEACTIVATED_V2:
            pid = payload["program_id"]
            if pid in self._programs:
                self._programs[pid]["status"] = "INACTIVE"

        elif event_type == PROMOTION_RULE_ADDED_V1:
            pid = payload["program_id"]
            if pid not in self._program_rules:
                self._program_rules[pid] = []
            self._program_rules[pid].append({
                "rule_id": payload["rule_id"],
                "rule_type": payload["rule_type"],
                "rule_params": payload.get("rule_params", {}),
            })

        elif event_type == PROMOTION_EVALUATED_V1:
            eid = payload["evaluation_id"]
            self._evaluations[eid] = {
                "sale_id": payload.get("sale_id"),
                "business_customer_id": payload.get("business_customer_id"),
                "applicable_programs": payload.get("applicable_programs", []),
            }

        elif event_type == PROMOTION_APPLIED_V1:
            aid = payload["application_id"]
            pid = payload["program_id"]
            self._applications[aid] = {
                "sale_id": payload["sale_id"],
                "program_id": pid,
                "discount_amount": payload["discount_amount"],
                "adjusted_net_amount": payload["adjusted_net_amount"],
                "tax_mode": payload["tax_mode"],
                "settlement": payload["settlement"],
            }
            self._total_discounts += payload["discount_amount"]
            if pid in self._programs:
                self._programs[pid]["usage_count"] += 1
                self._programs[pid]["total_discount_issued"] += payload["discount_amount"]

    # ── v1 queries ────────────────────────────────────────────
    def get_campaign(self, campaign_id: str) -> Optional[dict]:
        return self._campaigns.get(campaign_id)

    def get_coupon(self, coupon_id: str) -> Optional[dict]:
        return self._coupons.get(coupon_id)

    # ── v2 queries ────────────────────────────────────────────
    def get_program(self, program_id: str) -> Optional[dict]:
        return self._programs.get(program_id)

    def get_program_rules(self, program_id: str) -> List[dict]:
        return self._program_rules.get(program_id, [])

    def get_active_programs(self) -> List[dict]:
        return [p for p in self._programs.values() if p["status"] == "ACTIVE"]

    def get_evaluation(self, evaluation_id: str) -> Optional[dict]:
        return self._evaluations.get(evaluation_id)

    def get_application(self, application_id: str) -> Optional[dict]:
        return self._applications.get(application_id)

    def evaluate_basket(
        self,
        basket_items: List[dict],
        basket_net_amount: int,
        business_customer_id: Optional[str] = None,
    ) -> List[dict]:
        """Evaluate which active programs apply to this basket.

        Returns list of applicable programs with computed discount amounts.
        Handles composable rules, BUY_X_GET_Y, volume thresholds, etc.
        """
        applicable = []
        for program in self.get_active_programs():
            pid = program["program_id"]
            rules = self._program_rules.get(pid, [])
            discount = self._compute_discount(program, rules, basket_items, basket_net_amount)
            if discount > 0:
                applicable.append({
                    "program_id": pid,
                    "name": program["name"],
                    "timing": program["timing"],
                    "tax_mode": program["tax_mode"],
                    "settlement": program["settlement"],
                    "stackability": program["stackability"],
                    "stack_tags": program.get("stack_tags", []),
                    "discount_amount": discount,
                })
        return applicable

    def _compute_discount(
        self,
        program: dict,
        rules: List[dict],
        basket_items: List[dict],
        basket_net_amount: int,
    ) -> int:
        """Apply composable rules to compute total discount for this program."""
        discount = 0
        for rule in rules:
            rt = rule["rule_type"]
            rp = rule.get("rule_params", {})

            if rt == "PERCENTAGE":
                rate_bp = rp.get("rate_basis_points", 0)
                discount += basket_net_amount * rate_bp // 10000

            elif rt == "FIXED_AMOUNT":
                discount += rp.get("amount", 0)

            elif rt == "VOLUME_THRESHOLD":
                threshold = rp.get("min_amount", 0)
                if basket_net_amount >= threshold:
                    rate_bp = rp.get("rate_basis_points", 0)
                    discount += basket_net_amount * rate_bp // 10000

            elif rt == "BUY_X_GET_Y":
                buy_item = rp.get("buy_item_id")
                buy_qty = rp.get("buy_qty", 0)
                get_item = rp.get("get_item_id")
                get_qty = rp.get("get_qty", 0)
                # Find matching items in basket
                buy_count = sum(
                    i.get("quantity", 0)
                    for i in basket_items
                    if i.get("item_id") == buy_item
                )
                if buy_count >= buy_qty:
                    sets = buy_count // buy_qty
                    # Free items: look up get_item unit price
                    for item in basket_items:
                        if item.get("item_id") == get_item:
                            free_qty = min(sets * get_qty, item.get("quantity", 0))
                            discount += free_qty * item.get("unit_price", 0)
                            break

            elif rt == "BUNDLE":
                required = rp.get("required_items", [])
                bundle_discount = rp.get("discount_amount", 0)
                basket_ids = {i.get("item_id") for i in basket_items}
                if all(r in basket_ids for r in required):
                    discount += bundle_discount

        # Apply budget ceiling guard
        ceiling = program.get("budget_ceiling", 0)
        if ceiling > 0:
            issued = program.get("total_discount_issued", 0)
            remaining_budget = ceiling - issued
            discount = min(discount, max(0, remaining_budget))

        return discount

    @property
    def total_discounts(self) -> int:
        return self._total_discounts

    @property
    def event_count(self) -> int:
        return len(self._events)


PAYLOAD_BUILDERS = {
    # v1 (preserved)
    "promotion.campaign.create.request": build_campaign_created_payload,
    "promotion.campaign.activate.request": build_campaign_activated_payload,
    "promotion.campaign.deactivate.request": build_campaign_deactivated_payload,
    "promotion.coupon.issue.request": build_coupon_issued_payload,
    "promotion.coupon.redeem.request": build_coupon_redeemed_payload,
    # v2 (additive)
    **V2_PAYLOAD_BUILDERS,
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
        enforce_scope_guard(command)
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
