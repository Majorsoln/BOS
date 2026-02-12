"""
BOS Replay Engine — Checkpoints
=================================
Tracks replay progress to enable resume without reprocessing history.

Table: replay_checkpoints
Fields:
- projection_name: which projection was being rebuilt
- business_id: nullable (null = full system replay)
- last_event_id: last successfully processed event
- last_received_at: timestamp of last processed event (for ordering)
- updated_at: when checkpoint was saved

Checkpoints are NOT events. They are operational metadata.
They can be deleted, updated, or reset safely.
"""

import uuid

from django.db import models
from django.utils import timezone


class ReplayCheckpoint(models.Model):
    """
    Tracks replay progress for resumable projection rebuilds.
    """

    projection_name = models.CharField(
        max_length=255,
        help_text="Name of the projection being rebuilt.",
    )
    business_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Business scope. Null = full system replay.",
    )
    last_event_id = models.UUIDField(
        help_text="Last successfully processed event_id.",
    )
    last_received_at = models.DateTimeField(
        help_text="received_at of last processed event (for ordering).",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this checkpoint was last saved.",
    )

    class Meta:
        db_table = "replay_checkpoints"
        unique_together = [("projection_name", "business_id")]
        indexes = [
            models.Index(
                fields=["projection_name", "business_id"],
                name="idx_replay_proj_biz",
            ),
        ]

    def __str__(self):
        scope = self.business_id or "FULL"
        return (
            f"Checkpoint({self.projection_name}, "
            f"scope={scope}, "
            f"last={self.last_event_id})"
        )


# ══════════════════════════════════════════════════════════════
# CHECKPOINT OPERATIONS
# ══════════════════════════════════════════════════════════════

def save_checkpoint(
    projection_name: str,
    last_event_id: uuid.UUID,
    last_received_at,
    business_id: uuid.UUID = None,
) -> ReplayCheckpoint:
    """
    Save or update a replay checkpoint.
    """
    checkpoint, _ = ReplayCheckpoint.objects.update_or_create(
        projection_name=projection_name,
        business_id=business_id,
        defaults={
            "last_event_id": last_event_id,
            "last_received_at": last_received_at,
        },
    )
    return checkpoint


def load_checkpoint(
    projection_name: str,
    business_id: uuid.UUID = None,
) -> ReplayCheckpoint | None:
    """
    Load existing checkpoint for a projection.
    Returns None if no checkpoint exists.
    """
    try:
        return ReplayCheckpoint.objects.get(
            projection_name=projection_name,
            business_id=business_id,
        )
    except ReplayCheckpoint.DoesNotExist:
        return None


def clear_checkpoint(
    projection_name: str,
    business_id: uuid.UUID = None,
) -> bool:
    """
    Delete checkpoint for a projection.
    Returns True if deleted, False if not found.
    """
    deleted, _ = ReplayCheckpoint.objects.filter(
        projection_name=projection_name,
        business_id=business_id,
    ).delete()
    return deleted > 0
