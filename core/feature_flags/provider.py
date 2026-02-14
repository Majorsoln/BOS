"""
BOS Feature Flags - Provider Protocol and In-Memory Provider
=============================================================
"""

from __future__ import annotations

import uuid
from typing import Iterable, Protocol

from core.feature_flags.models import FeatureFlag


class FeatureFlagProvider(Protocol):
    def get_flags_for_business(
        self, business_id: uuid.UUID
    ) -> tuple[FeatureFlag, ...]:
        ...


class InMemoryFeatureFlagProvider:
    """
    Deterministic in-memory provider used by tests/bootstrap.
    """

    def __init__(self, flags: Iterable[FeatureFlag] | None = None):
        self._flags_by_business: dict[uuid.UUID, tuple[FeatureFlag, ...]] = {}

        dedupe: set[tuple[str, uuid.UUID, uuid.UUID | None]] = set()
        temp: dict[uuid.UUID, list[FeatureFlag]] = {}

        for flag in flags or ():
            scope = flag.scope_key()
            if scope in dedupe:
                raise ValueError(
                    "Duplicate feature flag scope "
                    f"(flag_key='{flag.flag_key}', "
                    f"business_id='{flag.business_id}', "
                    f"branch_id='{flag.branch_id}')."
                )
            dedupe.add(scope)
            temp.setdefault(flag.business_id, []).append(flag)

        for business_id, business_flags in temp.items():
            ordered = tuple(sorted(business_flags, key=lambda f: f.sort_key()))
            self._flags_by_business[business_id] = ordered

    def get_flags_for_business(
        self, business_id: uuid.UUID
    ) -> tuple[FeatureFlag, ...]:
        return self._flags_by_business.get(business_id, tuple())

