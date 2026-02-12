"""
BOS Event Store — Canonical Event Model
=========================================
Engine: Event Store (Core Infrastructure)
Authority: BOS Core Technical Appendix + Phase B Contract (FROZEN)

This is the ONLY writable record in the Event Store.
All truth in BOS is expressed as immutable events using this schema.

RULES (NON-NEGOTIABLE):
- No deletes, no overwrites, no updates after persistence
- Every event has exactly one actor (actor_type + actor_id)
- Hash-chain integrity via previous_event_hash → event_hash
- Status enum: FINAL | PROVISIONAL | REVIEW_REQUIRED
- Schema changes are additive only
- correlation_id is mandatory (every event belongs to a story)
- causation_id is nullable (first event in a chain has no cause)

This file contains NO business logic.
The Event Store validates structure and persists — it never interprets.
"""

import uuid
from django.db import models


# ══════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════

class EventStatus(models.TextChoices):
    """
    Event lifecycle status — replaces former provisional boolean.

    FINAL            — Confirmed, immutable, fully trusted.
    PROVISIONAL      — Created offline or pending sync. Awaits confirmation.
    REVIEW_REQUIRED  — Requires human review (offline conflict,
                       cash difference, inventory variance, AI advice).
    """
    FINAL = "FINAL", "Final"
    PROVISIONAL = "PROVISIONAL", "Provisional"
    REVIEW_REQUIRED = "REVIEW_REQUIRED", "Review Required"


class ActorType(models.TextChoices):
    """
    Actor type enum — every event has exactly one actor.
    AI is advisory only and cannot execute operations.
    """
    HUMAN = "HUMAN", "Human"
    SYSTEM = "SYSTEM", "System"
    DEVICE = "DEVICE", "Device"
    AI = "AI", "AI"


# ══════════════════════════════════════════════════════════════
# CANONICAL EVENT MODEL
# ══════════════════════════════════════════════════════════════

class Event(models.Model):
    """
    BOS Canonical Event Record
    ==========================
    The single, immutable unit of truth in BOS.
    Once persisted, an event is NEVER modified or deleted.
    Corrections are expressed as NEW events with correction_of set.

    Field groups:
        Identity & Classification
        Tenant Scope
        Engine & Actor
        Causality
        Payload & References
        Temporal
        Status & Correction
        Integrity (Hash-Chain)
    """

    # ── Identity & Classification ─────────────────────────────
    event_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique event identifier. Enforces idempotency.",
    )

    event_type = models.CharField(
        max_length=255,
        help_text=(
            "Namespaced event type from registry. "
            "Format: engine.domain.action (e.g. inventory.stock.moved)."
        ),
    )

    event_version = models.PositiveSmallIntegerField(
        help_text="Schema version of this event type's payload.",
    )

    # ── Tenant Scope ──────────────────────────────────────────
    business_id = models.UUIDField(
        help_text="Business tenant boundary. Always required.",
    )

    branch_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Branch scope. Nullable for business-wide events.",
    )

    # ── Engine & Actor ────────────────────────────────────────
    source_engine = models.CharField(
        max_length=100,
        help_text=(
            "Engine that emitted this event. "
            "Each engine writes only its own events."
        ),
    )

    actor_type = models.CharField(
        max_length=20,
        choices=ActorType.choices,
        help_text="Type of actor: HUMAN, SYSTEM, DEVICE, or AI.",
    )

    actor_id = models.CharField(
        max_length=255,
        help_text=(
            "Unique identifier of the actor "
            "(user ID, system ID, device ID, AI agent ID)."
        ),
    )

    # ── Causality (first-class, not metadata) ─────────────────
    correlation_id = models.UUIDField(
        help_text=(
            "Groups events belonging to the same story/journey "
            "(e.g. a full checkout flow). Required — every event "
            "belongs to a story."
        ),
    )

    causation_id = models.UUIDField(
        null=True,
        blank=True,
        help_text=(
            "The event_id that directly caused this event. "
            "Nullable — the first event in a causal chain has no cause."
        ),
    )

    # ── Payload & References ──────────────────────────────────
    payload = models.JSONField(
        help_text=(
            "Versioned event payload. Structure governed by "
            "event_type + event_version. Part of the event envelope."
        ),
    )

    reference = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Optional external reference context "
            "(e.g. receipt ID, PO number)."
        ),
    )

    # ── Temporal ──────────────────────────────────────────────
    created_at = models.DateTimeField(
        help_text="When the event was created at source.",
    )

    received_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the Event Store received and persisted this event.",
    )

    # ── Status & Correction ───────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.FINAL,
        help_text=(
            "FINAL — trusted and confirmed. "
            "PROVISIONAL — offline/pending sync. "
            "REVIEW_REQUIRED — needs human review."
        ),
    )

    correction_of = models.UUIDField(
        null=True,
        blank=True,
        help_text=(
            "References event_id of the event this corrects. "
            "Null if not a correction."
        ),
    )

    # ── Integrity (Hash-Chain) ────────────────────────────────
    previous_event_hash = models.CharField(
        max_length=64,
        help_text=(
            "SHA-256 hash of the immediately preceding event. "
            "Empty string for the very first event in the chain."
        ),
    )

    event_hash = models.CharField(
        max_length=64,
        help_text=(
            "SHA-256 hash of this event's content + previous_event_hash. "
            "Ensures tamper-evident, audit-proof chain integrity."
        ),
    )

    # ══════════════════════════════════════════════════════════
    # META & INDEXING
    # ══════════════════════════════════════════════════════════

    class Meta:
        db_table = "bos_event_store"
        ordering = ["received_at"]
        indexes = [
            models.Index(
                fields=["business_id", "received_at"],
                name="idx_evt_business_time",
            ),
            models.Index(
                fields=["event_type"],
                name="idx_evt_type",
            ),
            models.Index(
                fields=["source_engine"],
                name="idx_evt_source_engine",
            ),
            models.Index(
                fields=["status"],
                name="idx_evt_status",
            ),
            models.Index(
                fields=["correction_of"],
                name="idx_evt_correction_of",
            ),
            models.Index(
                fields=["correlation_id"],
                name="idx_evt_correlation",
            ),
            models.Index(
                fields=["causation_id"],
                name="idx_evt_causation",
            ),
        ]

    # ══════════════════════════════════════════════════════════
    # IMMUTABILITY GUARDS
    # ══════════════════════════════════════════════════════════

    def save(self, *args, **kwargs):
        """
        GUARD: INSERT only. No updates to persisted events.
        Corrections must be new events with correction_of set.
        """
        if not self._state.adding:
            raise PermissionError(
                "BOS DOCTRINE VIOLATION: Events are immutable. "
                "Cannot update a persisted event. "
                "Corrections must be new events with correction_of set."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        GUARD: Events are NEVER deleted. Non-negotiable.
        """
        raise PermissionError(
            "BOS DOCTRINE VIOLATION: Events are NEVER deleted. "
            "This is a non-negotiable rule."
        )

    def __str__(self):
        return f"[{self.event_type}] {self.event_id} ({self.status})"
