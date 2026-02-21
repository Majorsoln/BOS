"""
BOS AI Module — Advisory Only
================================
AI components are advisory only. AI CANNOT commit state autonomously.
All AI interactions are journaled for full audit trail.
"""

from ai.guardrails import (
    AIActionType,
    GuardrailResult,
    check_ai_guardrail,
    ai_rejection_reason,
)

__all__ = [
    "AIActionType",
    "GuardrailResult",
    "check_ai_guardrail",
    "ai_rejection_reason",
]
