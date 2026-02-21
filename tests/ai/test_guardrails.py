"""
Tests for ai.guardrails — AI execution boundary enforcement.
"""

import uuid
import pytest

from ai.guardrails import (
    AIActionType,
    GuardrailResult,
    check_ai_guardrail,
    ai_rejection_reason,
    FORBIDDEN_OPERATIONS,
)


BIZ_ID = uuid.uuid4()


class TestGuardrailAlwaysAllowed:
    """Read-only advisory actions should always be allowed."""

    @pytest.mark.parametrize("action_type", [
        AIActionType.ANALYZE,
        AIActionType.RECOMMEND,
        AIActionType.SIMULATE,
        AIActionType.FLAG_ANOMALY,
    ])
    def test_advisory_actions_allowed(self, action_type):
        result = check_ai_guardrail(
            action_type=action_type,
            operation_name="read_projection",
            business_id=BIZ_ID,
            actor_business_id=BIZ_ID,
        )
        assert result.allowed
        assert not result.requires_human_approval


class TestGuardrailCrossTenant:
    """AI must never access data from another tenant."""

    def test_cross_tenant_denied(self):
        other_biz = uuid.uuid4()
        result = check_ai_guardrail(
            action_type=AIActionType.ANALYZE,
            operation_name="read_projection",
            business_id=BIZ_ID,
            actor_business_id=other_biz,
        )
        assert not result.allowed
        assert "cross-tenant" in result.reason.lower()

    def test_same_tenant_allowed(self):
        result = check_ai_guardrail(
            action_type=AIActionType.ANALYZE,
            operation_name="read_projection",
            business_id=BIZ_ID,
            actor_business_id=BIZ_ID,
        )
        assert result.allowed


class TestGuardrailForbiddenOperations:
    """Certain operations are absolutely forbidden for AI."""

    @pytest.mark.parametrize("operation", list(FORBIDDEN_OPERATIONS))
    def test_forbidden_operations_denied(self, operation):
        result = check_ai_guardrail(
            action_type=AIActionType.ANALYZE,
            operation_name=operation,
            business_id=BIZ_ID,
            actor_business_id=BIZ_ID,
        )
        assert not result.allowed
        assert "forbidden" in result.reason.lower()


class TestGuardrailCommandPreparation:
    """Command preparation requires human approval."""

    def test_prepare_command_requires_approval(self):
        result = check_ai_guardrail(
            action_type=AIActionType.PREPARE_COMMAND,
            operation_name="draft_reorder",
            business_id=BIZ_ID,
            actor_business_id=BIZ_ID,
        )
        assert result.allowed
        assert result.requires_human_approval


class TestGuardrailAutonomousExecution:
    """Autonomous execution requires explicit policy grant."""

    def test_execute_denied_without_policy(self):
        result = check_ai_guardrail(
            action_type=AIActionType.EXECUTE_COMMAND,
            operation_name="auto_reorder",
            business_id=BIZ_ID,
            actor_business_id=BIZ_ID,
            has_automation_policy=False,
        )
        assert not result.allowed

    def test_execute_allowed_with_policy(self):
        result = check_ai_guardrail(
            action_type=AIActionType.EXECUTE_COMMAND,
            operation_name="auto_reorder",
            business_id=BIZ_ID,
            actor_business_id=BIZ_ID,
            has_automation_policy=True,
        )
        assert result.allowed
        assert not result.requires_human_approval


class TestAIRejectionReason:
    """Test conversion of denied guardrails to RejectionReason."""

    def test_denied_produces_rejection_reason(self):
        result = check_ai_guardrail(
            action_type=AIActionType.EXECUTE_COMMAND,
            operation_name="auto_reorder",
            business_id=BIZ_ID,
            actor_business_id=BIZ_ID,
            has_automation_policy=False,
        )
        rejection = ai_rejection_reason(result)
        assert rejection is not None
        assert rejection.code == "AI_EXECUTION_FORBIDDEN"
        assert rejection.policy_name == "check_ai_guardrail"

    def test_allowed_produces_no_rejection(self):
        result = check_ai_guardrail(
            action_type=AIActionType.ANALYZE,
            operation_name="read_data",
            business_id=BIZ_ID,
            actor_business_id=BIZ_ID,
        )
        assert ai_rejection_reason(result) is None
