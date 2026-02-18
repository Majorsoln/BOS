"""
BOS Auth - Persistent API Key Credentials
=========================================
Stores API-key credentials in Postgres for deterministic auth resolution.
"""

from __future__ import annotations

import uuid

from django.db import models


class ApiKeyStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    REVOKED = "REVOKED", "Revoked"


class ApiKeyActorType(models.TextChoices):
    HUMAN = "HUMAN", "Human"
    SYSTEM = "SYSTEM", "System"
    DEVICE = "DEVICE", "Device"
    AI = "AI", "AI"


class ApiKeyCredential(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    key_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
    )
    label = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    actor_id = models.CharField(max_length=255)
    actor_type = models.CharField(
        max_length=20,
        choices=ApiKeyActorType.choices,
    )
    allowed_business_ids = models.JSONField(default=list)
    allowed_branch_ids_by_business = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=ApiKeyStatus.choices,
        default=ApiKeyStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_by_actor_id = models.CharField(max_length=255)
    revoked_by_actor_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "bos_api_key_credentials"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="idx_api_key_status_created"),
        ]

    def __str__(self) -> str:
        return f"{self.id} ({self.status})"
