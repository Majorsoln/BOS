from __future__ import annotations

import uuid

import pytest

from core.replay.errors import ReplayError
from core.replay.scope import ReplayScope, validate_replay_scope


def test_default_business_scope_requires_business_id():
    with pytest.raises(ReplayError, match="business_id is required"):
        validate_replay_scope(
            business_id=None,
            replay_scope=ReplayScope.BUSINESS,
        )


def test_unscoped_replay_requires_explicit_intent():
    with pytest.raises(ReplayError, match="business_id is required"):
        validate_replay_scope(
            business_id=None,
            replay_scope=ReplayScope.BUSINESS,
        )

    resolved = validate_replay_scope(
        business_id=None,
        replay_scope=ReplayScope.UNSCOPED,
    )
    assert resolved == ReplayScope.UNSCOPED


def test_unscoped_replay_rejects_business_id():
    with pytest.raises(
        ReplayError,
        match="business_id must be None",
    ):
        validate_replay_scope(
            business_id=uuid.uuid4(),
            replay_scope=ReplayScope.UNSCOPED,
        )

