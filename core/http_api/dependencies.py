"""
BOS HTTP API - Dependencies
===========================
Injected providers for non-deterministic metadata and handler wiring.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


class IdProvider(Protocol):
    def new_command_id(self) -> uuid.UUID:
        ...

    def new_correlation_id(self) -> uuid.UUID:
        ...


class Clock(Protocol):
    def now_issued_at(self) -> datetime:
        ...


class UuidIdProvider:
    def new_command_id(self) -> uuid.UUID:
        return uuid.uuid4()

    def new_correlation_id(self) -> uuid.UUID:
        return uuid.uuid4()


class UtcClock:
    def now_issued_at(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True)
class HttpApiDependencies:
    admin_service: object
    admin_repository: object
    id_provider: IdProvider
    clock: Clock

