"""
Tests for BOS SaaS — Tenant Onboarding Automation
"""

import uuid
from datetime import datetime

import pytest

from core.saas.onboarding import (
    ONBOARDING_COMPLETED_V1,
    ONBOARDING_INITIATED_V1,
    ONBOARDING_STEP_COMPLETED_V1,
    AbandonOnboardingRequest,
    CompleteStepRequest,
    InitiateOnboardingRequest,
    OnboardingProjection,
    OnboardingService,
    OnboardingStatus,
    OnboardingStep,
)


NOW = datetime(2025, 6, 1, 12, 0, 0)


@pytest.fixture
def projection():
    return OnboardingProjection()


@pytest.fixture
def service(projection):
    return OnboardingService(projection)


def _initiate(service):
    return service.initiate(InitiateOnboardingRequest(
        business_name="Acme Ltd",
        country_code="TZ",
        timezone="Africa/Dar_es_Salaam",
        contact_email="admin@acme.co.tz",
        actor_id="system",
        issued_at=NOW,
    ))


def _complete_step(service, ob_id, step, step_data=None):
    return service.complete_step(CompleteStepRequest(
        onboarding_id=ob_id,
        step=step,
        actor_id="system",
        issued_at=NOW,
        step_data=step_data,
    ))


class TestOnboardingInitiation:
    def test_initiate_returns_id(self, service):
        result = _initiate(service)
        assert "onboarding_id" in result
        assert isinstance(result["onboarding_id"], uuid.UUID)

    def test_initiate_emits_event(self, service):
        result = _initiate(service)
        assert result["events"][0]["event_type"] == ONBOARDING_INITIATED_V1

    def test_flow_exists_in_projection(self, service, projection):
        result = _initiate(service)
        flow = projection.get_flow(result["onboarding_id"])
        assert flow is not None
        assert flow.business_name == "Acme Ltd"
        assert flow.current_step == OnboardingStep.INITIATED
        assert flow.status == OnboardingStatus.IN_PROGRESS


class TestOnboardingStepProgression:
    def test_complete_business_created_step(self, service, projection):
        result = _initiate(service)
        ob_id = result["onboarding_id"]
        biz_id = uuid.uuid4()
        rejection = _complete_step(service, ob_id, "BUSINESS_CREATED", {
            "business_id": str(biz_id),
        })
        assert rejection is None
        flow = projection.get_flow(ob_id)
        assert flow.current_step == OnboardingStep.BUSINESS_CREATED
        assert flow.business_id == biz_id

    def test_full_onboarding_flow(self, service, projection):
        result = _initiate(service)
        ob_id = result["onboarding_id"]
        biz_id = uuid.uuid4()
        plan_id = uuid.uuid4()
        branch_id = uuid.uuid4()

        _complete_step(service, ob_id, "BUSINESS_CREATED", {"business_id": str(biz_id)})
        _complete_step(service, ob_id, "PLAN_SELECTED", {"plan_id": str(plan_id)})
        _complete_step(service, ob_id, "BRANCH_CREATED", {"branch_id": str(branch_id)})
        _complete_step(service, ob_id, "ADMIN_SETUP", {})

        flow = projection.get_flow(ob_id)
        assert flow.status == OnboardingStatus.COMPLETED
        assert flow.business_id == biz_id
        assert flow.plan_id == plan_id
        assert flow.branch_id == branch_id

    def test_step_out_of_order_rejected(self, service):
        result = _initiate(service)
        ob_id = result["onboarding_id"]
        # Try to skip BUSINESS_CREATED and go to PLAN_SELECTED
        rejection = _complete_step(service, ob_id, "PLAN_SELECTED")
        assert rejection is not None
        assert rejection.code == "STEP_OUT_OF_ORDER"

    def test_invalid_step_rejected(self, service):
        result = _initiate(service)
        ob_id = result["onboarding_id"]
        rejection = _complete_step(service, ob_id, "INVALID_STEP")
        assert rejection is not None
        assert rejection.code == "INVALID_STEP"

    def test_step_on_nonexistent_flow_rejected(self, service):
        rejection = _complete_step(service, uuid.uuid4(), "BUSINESS_CREATED")
        assert rejection is not None
        assert rejection.code == "ONBOARDING_NOT_FOUND"


class TestOnboardingAbandonment:
    def test_abandon_in_progress_flow(self, service, projection):
        result = _initiate(service)
        ob_id = result["onboarding_id"]
        rejection = service.abandon(AbandonOnboardingRequest(
            onboarding_id=ob_id, actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is None
        flow = projection.get_flow(ob_id)
        assert flow.status == OnboardingStatus.ABANDONED

    def test_abandon_completed_flow_rejected(self, service):
        result = _initiate(service)
        ob_id = result["onboarding_id"]
        _complete_step(service, ob_id, "BUSINESS_CREATED", {"business_id": str(uuid.uuid4())})
        _complete_step(service, ob_id, "PLAN_SELECTED", {"plan_id": str(uuid.uuid4())})
        _complete_step(service, ob_id, "BRANCH_CREATED", {"branch_id": str(uuid.uuid4())})
        _complete_step(service, ob_id, "ADMIN_SETUP", {})
        rejection = service.abandon(AbandonOnboardingRequest(
            onboarding_id=ob_id, actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "ONBOARDING_NOT_IN_PROGRESS"

    def test_abandon_nonexistent_rejected(self, service):
        rejection = service.abandon(AbandonOnboardingRequest(
            onboarding_id=uuid.uuid4(), actor_id="admin-1", issued_at=NOW,
        ))
        assert rejection is not None
        assert rejection.code == "ONBOARDING_NOT_FOUND"


class TestOnboardingProgress:
    def test_progress_initial(self, service):
        result = _initiate(service)
        progress = service.get_progress(result["onboarding_id"])
        assert progress is not None
        assert progress["current_step"] == "INITIATED"
        assert progress["progress_pct"] > 0

    def test_progress_midway(self, service):
        result = _initiate(service)
        ob_id = result["onboarding_id"]
        _complete_step(service, ob_id, "BUSINESS_CREATED", {"business_id": str(uuid.uuid4())})
        _complete_step(service, ob_id, "PLAN_SELECTED", {"plan_id": str(uuid.uuid4())})
        progress = service.get_progress(ob_id)
        assert progress["current_step"] == "PLAN_SELECTED"
        assert len(progress["completed_steps"]) == 3  # INITIATED + 2 steps

    def test_progress_nonexistent_returns_none(self, service):
        assert service.get_progress(uuid.uuid4()) is None


class TestOnboardingProjectionQueries:
    def test_list_in_progress(self, service, projection):
        _initiate(service)
        _initiate(service)
        assert len(projection.list_in_progress()) == 2

    def test_list_completed(self, service, projection):
        result = _initiate(service)
        ob_id = result["onboarding_id"]
        _complete_step(service, ob_id, "BUSINESS_CREATED", {"business_id": str(uuid.uuid4())})
        _complete_step(service, ob_id, "PLAN_SELECTED", {"plan_id": str(uuid.uuid4())})
        _complete_step(service, ob_id, "BRANCH_CREATED", {"branch_id": str(uuid.uuid4())})
        _complete_step(service, ob_id, "ADMIN_SETUP", {})
        assert len(projection.list_completed()) == 1

    def test_truncate(self, service, projection):
        _initiate(service)
        projection.truncate()
        assert len(projection.list_in_progress()) == 0
