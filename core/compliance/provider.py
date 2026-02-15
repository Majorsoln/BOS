"""
BOS Compliance - Provider Protocol and In-Memory Provider
=========================================================
"""

from __future__ import annotations

import uuid
from typing import Iterable, Protocol

from core.compliance.models import ComplianceProfile


class ComplianceProvider(Protocol):
    def get_profiles_for_business(
        self,
        business_id: uuid.UUID,
    ) -> tuple[ComplianceProfile, ...]:
        ...


class InMemoryComplianceProvider:
    """
    Deterministic in-memory provider used in tests/bootstrap.
    Enforces strict uniqueness per (business_id, branch_id, version).
    """

    def __init__(
        self,
        profiles: Iterable[ComplianceProfile] | None = None,
    ):
        self._profiles_by_business: dict[
            uuid.UUID, tuple[ComplianceProfile, ...]
        ] = {}

        dedupe: set[tuple[uuid.UUID, uuid.UUID | None, int]] = set()
        temp: dict[uuid.UUID, list[ComplianceProfile]] = {}

        for profile in profiles or ():
            dedupe_key = (
                profile.business_id,
                profile.branch_id,
                profile.version,
            )
            if dedupe_key in dedupe:
                raise ValueError(
                    "Duplicate compliance profile scope/version "
                    f"(business_id='{profile.business_id}', "
                    f"branch_id='{profile.branch_id}', "
                    f"version='{profile.version}')."
                )
            dedupe.add(dedupe_key)
            temp.setdefault(profile.business_id, []).append(profile)

        for business_id, business_profiles in temp.items():
            ordered = tuple(
                sorted(
                    business_profiles,
                    key=lambda profile: profile.sort_key(),
                )
            )
            self._profiles_by_business[business_id] = ordered

    def get_profiles_for_business(
        self,
        business_id: uuid.UUID,
    ) -> tuple[ComplianceProfile, ...]:
        return self._profiles_by_business.get(business_id, tuple())

