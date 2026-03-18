"""
Tests for BOS SaaS — Engine Combos & Region-Aware Pricing
"""

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from core.saas.plans import (
    COMBO_DEFINED_V1,
    COMBO_DEACTIVATED_V1,
    COMBO_UPDATED_V1,
    COMBO_RATE_SET_V1,
    ENGINE_REGISTERED_V1,
    BusinessModel,
    ComboDefinition,
    ComboStatus,
    DeactivateComboRequest,
    DefineComboRequest,
    FREE_ENGINE_KEYS,
    PlanManager,
    PlanProjection,
    PlanQuota,
    RegisterEngineRequest,
    SetComboRateRequest,
    UpdateComboRequest,
)


NOW = datetime(2025, 6, 1, 12, 0, 0)


@pytest.fixture
def projection():
    return PlanProjection()


@pytest.fixture
def manager(projection):
    return PlanManager(projection)


def _register_engines(manager):
    for key, name, cat in [
        ("retail", "Retail POS", "PAID"),
        ("accounting", "Accounting", "PAID"),
        ("inventory", "Inventory", "PAID"),
    ]:
        manager.register_engine(RegisterEngineRequest(
            engine_key=key, display_name=name,
            category=cat, description=f"{name} engine",
            actor_id="admin-1", issued_at=NOW,
        ))


def _define_duka(manager):
    _register_engines(manager)
    return manager.define_combo(DefineComboRequest(
        name="BOS Duka",
        slug="bos-duka",
        description="Retail + Accounting for shops",
        business_model="B2C",
        paid_engines=("retail", "accounting"),
        max_branches=1,
        max_users=3,
        max_api_calls_per_month=1000,
        max_documents_per_month=100,
        sort_order=1,
        actor_id="admin-1",
        issued_at=NOW,
    ))


class TestComboDefinition:
    def test_define_combo_returns_combo_id(self, manager):
        result = _define_duka(manager)
        assert "combo_id" in result
        assert isinstance(result["combo_id"], uuid.UUID)

    def test_define_combo_emits_event(self, manager):
        result = _define_duka(manager)
        assert len(result["events"]) == 1
        assert result["events"][0]["event_type"] == COMBO_DEFINED_V1

    def test_combo_exists_in_projection(self, manager, projection):
        result = _define_duka(manager)
        combo = projection.get_combo(result["combo_id"])
        assert combo is not None
        assert combo.name == "BOS Duka"
        assert combo.business_model == BusinessModel.B2C
        assert combo.status == ComboStatus.ACTIVE

    def test_combo_engines_are_frozenset(self, manager, projection):
        result = _define_duka(manager)
        combo = projection.get_combo(result["combo_id"])
        assert combo.paid_engines == frozenset({"retail", "accounting"})

    def test_combo_all_engines_includes_free(self, manager, projection):
        result = _define_duka(manager)
        combo = projection.get_combo(result["combo_id"])
        assert FREE_ENGINE_KEYS.issubset(combo.all_engines)
        assert "retail" in combo.all_engines
        assert "accounting" in combo.all_engines

    def test_combo_quota_values(self, manager, projection):
        result = _define_duka(manager)
        combo = projection.get_combo(result["combo_id"])
        assert combo.quota.max_branches == 1
        assert combo.quota.max_users == 3
        assert combo.quota.max_api_calls_per_month == 1000

    def test_invalid_business_model_rejected(self, manager):
        _register_engines(manager)
        result = manager.define_combo(DefineComboRequest(
            name="Invalid",
            slug="invalid",
            description="Bad model",
            business_model="INVALID_MODEL",
            paid_engines=("retail",),
            max_branches=1,
            max_users=1,
            max_api_calls_per_month=100,
            max_documents_per_month=10,
            sort_order=0,
            actor_id="admin-1",
            issued_at=NOW,
        ))
        assert "rejected" in result
        assert result["rejected"].code == "INVALID_BUSINESS_MODEL"

    def test_duplicate_slug_rejected(self, manager):
        _define_duka(manager)
        result = manager.define_combo(DefineComboRequest(
            name="BOS Duka 2",
            slug="bos-duka",
            description="Duplicate slug",
            business_model="B2C",
            paid_engines=("retail",),
            max_branches=1,
            max_users=1,
            max_api_calls_per_month=100,
            max_documents_per_month=10,
            sort_order=0,
            actor_id="admin-1",
            issued_at=NOW,
        ))
        assert "rejected" in result
        assert result["rejected"].code == "COMBO_SLUG_EXISTS"


class TestComboUpdate:
    def test_update_combo_name(self, manager, projection):
        result = _define_duka(manager)
        combo_id = result["combo_id"]
        rejection = manager.update_combo(UpdateComboRequest(
            combo_id=combo_id,
            name="BOS Duka Plus",
            actor_id="admin-1",
            issued_at=NOW,
        ))
        assert rejection is None
        combo = projection.get_combo(combo_id)
        assert combo.name == "BOS Duka Plus"

    def test_update_combo_engines(self, manager, projection):
        result = _define_duka(manager)
        combo_id = result["combo_id"]
        manager.update_combo(UpdateComboRequest(
            combo_id=combo_id,
            paid_engines=("retail", "accounting", "inventory"),
            actor_id="admin-1",
            issued_at=NOW,
        ))
        combo = projection.get_combo(combo_id)
        assert "inventory" in combo.paid_engines

    def test_update_nonexistent_combo_rejected(self, manager):
        rejection = manager.update_combo(UpdateComboRequest(
            combo_id=uuid.uuid4(),
            name="Ghost",
            actor_id="admin-1",
            issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "COMBO_NOT_FOUND"

    def test_update_deactivated_combo_rejected(self, manager):
        result = _define_duka(manager)
        combo_id = result["combo_id"]
        manager.deactivate_combo(DeactivateComboRequest(
            combo_id=combo_id, actor_id="admin-1", issued_at=NOW,
        ))
        rejection = manager.update_combo(UpdateComboRequest(
            combo_id=combo_id, name="Revived", actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "COMBO_DEACTIVATED"


class TestComboDeactivation:
    def test_deactivate_combo(self, manager, projection):
        result = _define_duka(manager)
        combo_id = result["combo_id"]
        rejection = manager.deactivate_combo(DeactivateComboRequest(
            combo_id=combo_id, actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is None
        combo = projection.get_combo(combo_id)
        assert combo.status == ComboStatus.DEACTIVATED

    def test_double_deactivate_rejected(self, manager):
        result = _define_duka(manager)
        combo_id = result["combo_id"]
        manager.deactivate_combo(DeactivateComboRequest(
            combo_id=combo_id, actor_id="admin-1", issued_at=NOW,
        ))
        rejection = manager.deactivate_combo(DeactivateComboRequest(
            combo_id=combo_id, actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "COMBO_ALREADY_DEACTIVATED"

    def test_deactivated_combo_not_in_active_list(self, manager, projection):
        result = _define_duka(manager)
        combo_id = result["combo_id"]
        manager.deactivate_combo(DeactivateComboRequest(
            combo_id=combo_id, actor_id="admin-1", issued_at=NOW,
        ))
        assert len(projection.list_combos(active_only=True)) == 0


class TestComboEngineResolution:
    def test_resolve_engines_for_combo(self, manager):
        result = _define_duka(manager)
        engines = manager.resolve_engines_for_combo(result["combo_id"])
        assert "retail" in engines
        assert "accounting" in engines
        assert FREE_ENGINE_KEYS.issubset(engines)

    def test_resolve_engines_for_missing_combo(self, manager):
        engines = manager.resolve_engines_for_combo(uuid.uuid4())
        assert engines == FREE_ENGINE_KEYS


class TestComboQuotaCheck:
    def test_quota_within_limit(self, manager):
        result = _define_duka(manager)
        rejection = manager.check_quota(result["combo_id"], "branches", 0)
        assert rejection is None

    def test_quota_exceeded(self, manager):
        result = _define_duka(manager)
        rejection = manager.check_quota(result["combo_id"], "branches", 1)
        assert rejection is not None
        assert rejection.code == "QUOTA_EXCEEDED"

    def test_quota_unknown_resource_passes(self, manager):
        result = _define_duka(manager)
        rejection = manager.check_quota(result["combo_id"], "unknown_resource", 999)
        assert rejection is None

    def test_quota_no_active_combo(self, manager):
        rejection = manager.check_quota(uuid.uuid4(), "branches", 0)
        assert rejection is not None
        assert rejection.code == "NO_ACTIVE_COMBO"


class TestComboRates:
    def test_set_rate_for_region(self, manager, projection):
        result = _define_duka(manager)
        combo_id = result["combo_id"]
        rate_result = manager.set_combo_rate(SetComboRateRequest(
            combo_id=combo_id,
            region_code="KE",
            currency="KES",
            monthly_amount=Decimal("4500"),
            actor_id="admin-1",
            issued_at=NOW,
        ))
        assert "events" in rate_result
        rate = projection.get_rate(combo_id, "KE")
        assert rate is not None
        assert rate.monthly_amount == Decimal("4500")
        assert rate.currency == "KES"

    def test_pricing_catalog(self, manager, projection):
        result = _define_duka(manager)
        combo_id = result["combo_id"]
        manager.set_combo_rate(SetComboRateRequest(
            combo_id=combo_id,
            region_code="KE",
            currency="KES",
            monthly_amount=Decimal("4500"),
            actor_id="admin-1",
            issued_at=NOW,
        ))
        catalog = manager.get_pricing_catalog("KE")
        assert len(catalog) == 1
        assert catalog[0]["name"] == "BOS Duka"
        assert catalog[0]["monthly_amount"] == "4500"

    def test_pricing_catalog_filtered_by_model(self, manager, projection):
        result = _define_duka(manager)
        combo_id = result["combo_id"]
        manager.set_combo_rate(SetComboRateRequest(
            combo_id=combo_id,
            region_code="KE",
            currency="KES",
            monthly_amount=Decimal("4500"),
            actor_id="admin-1",
            issued_at=NOW,
        ))
        # B2C matches
        assert len(manager.get_pricing_catalog("KE", business_model="B2C")) == 1
        # B2B should not match a B2C combo
        assert len(manager.get_pricing_catalog("KE", business_model="B2B")) == 0


class TestPlanProjectionQueries:
    def test_list_combos(self, manager, projection):
        _define_duka(manager)
        assert len(projection.list_combos()) == 1

    def test_get_combo_by_slug(self, manager, projection):
        _define_duka(manager)
        combo = projection.get_combo_by_slug("bos-duka")
        assert combo is not None
        assert combo.name == "BOS Duka"

    def test_list_engines(self, manager, projection):
        _register_engines(manager)
        engines = projection.list_engines()
        assert len(engines) == 3

    def test_truncate(self, manager, projection):
        _define_duka(manager)
        projection.truncate()
        assert len(projection.list_combos()) == 0
