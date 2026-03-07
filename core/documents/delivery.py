"""
BOS Documents — Delivery Service
=================================
Delivers issued documents to recipients via configured channels.

Channels:
- EMAIL: Send PDF/HTML as email attachment or inline
- SMS: Send short link to hosted document
- WHATSAPP: Send PDF via WhatsApp Business API

Architecture:
- DocumentDeliveryService orchestrates delivery
- Each channel is a DeliveryChannel implementation
- Delivery is async-safe (fire-and-forget from document issuance)
- Failed deliveries are logged, never block issuance

Usage:
    service = DocumentDeliveryService()
    service.register_channel("EMAIL", EmailDeliveryChannel(...))
    service.deliver(document_id=..., recipient=..., channel="EMAIL")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger("bos.documents.delivery")


# ══════════════════════════════════════════════════════════════
# DELIVERY CHANNEL PROTOCOL
# ══════════════════════════════════════════════════════════════

class DeliveryChannel(Protocol):
    """Interface that all delivery channel implementations must satisfy."""

    def send(self, *, request: "DeliveryRequest") -> "DeliveryResult":
        """Send a document to the recipient. Returns a DeliveryResult."""
        ...


# ══════════════════════════════════════════════════════════════
# DATA CLASSES
# ══════════════════════════════════════════════════════════════

VALID_CHANNELS = frozenset({"EMAIL", "SMS", "WHATSAPP"})
VALID_DELIVERY_STATUSES = frozenset({"PENDING", "SENT", "DELIVERED", "FAILED"})


@dataclass(frozen=True)
class DeliveryRequest:
    """A request to deliver a document to a recipient."""
    document_id: str
    doc_type: str
    business_id: str
    recipient_name: str
    recipient_contact: str       # email, phone number, or WhatsApp number
    channel: str                 # EMAIL, SMS, WHATSAPP
    render_format: str = "PDF"   # PDF or HTML
    subject: str = ""            # email subject line
    message: str = ""            # optional body/message text
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if not self.document_id:
            raise ValueError("document_id must be non-empty.")
        if self.channel not in VALID_CHANNELS:
            raise ValueError(f"channel must be one of {sorted(VALID_CHANNELS)}.")
        if not self.recipient_contact:
            raise ValueError("recipient_contact must be non-empty.")


@dataclass(frozen=True)
class DeliveryResult:
    """Result of a delivery attempt."""
    document_id: str
    channel: str
    status: str                  # SENT, DELIVERED, FAILED
    provider_reference: str = "" # external ID from email/SMS/WhatsApp provider
    error_message: str = ""
    delivered_at: Optional[datetime] = None


# ══════════════════════════════════════════════════════════════
# STUB CHANNEL IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════

class EmailDeliveryChannel:
    """
    Email delivery stub.

    Production implementation should integrate with:
    - Django send_mail / django-anymail
    - AWS SES
    - SendGrid / Mailgun / Postmark
    """

    def send(self, *, request: DeliveryRequest) -> DeliveryResult:
        logger.info(
            "EMAIL stub: would send %s (%s) to %s <%s>",
            request.doc_type, request.document_id,
            request.recipient_name, request.recipient_contact,
        )
        return DeliveryResult(
            document_id=request.document_id,
            channel="EMAIL",
            status="SENT",
            provider_reference=f"stub-email-{request.document_id}",
            delivered_at=datetime.now(tz=timezone.utc),
        )


class SMSDeliveryChannel:
    """
    SMS delivery stub.

    Production implementation should integrate with:
    - Africa's Talking (East Africa)
    - Twilio
    - Nexmo / Vonage
    """

    def send(self, *, request: DeliveryRequest) -> DeliveryResult:
        logger.info(
            "SMS stub: would send link for %s (%s) to %s",
            request.doc_type, request.document_id, request.recipient_contact,
        )
        return DeliveryResult(
            document_id=request.document_id,
            channel="SMS",
            status="SENT",
            provider_reference=f"stub-sms-{request.document_id}",
            delivered_at=datetime.now(tz=timezone.utc),
        )


class WhatsAppDeliveryChannel:
    """
    WhatsApp delivery stub.

    Production implementation should integrate with:
    - WhatsApp Business API (Cloud API)
    - WhatsApp Business API via Twilio
    """

    def send(self, *, request: DeliveryRequest) -> DeliveryResult:
        logger.info(
            "WHATSAPP stub: would send %s (%s) to %s",
            request.doc_type, request.document_id, request.recipient_contact,
        )
        return DeliveryResult(
            document_id=request.document_id,
            channel="WHATSAPP",
            status="SENT",
            provider_reference=f"stub-whatsapp-{request.document_id}",
            delivered_at=datetime.now(tz=timezone.utc),
        )


# ══════════════════════════════════════════════════════════════
# DELIVERY SERVICE
# ══════════════════════════════════════════════════════════════

class DocumentDeliveryService:
    """
    Orchestrates document delivery across channels.

    Usage:
        service = DocumentDeliveryService()
        service.register_channel("EMAIL", EmailDeliveryChannel())
        service.register_channel("SMS", SMSDeliveryChannel())
        service.register_channel("WHATSAPP", WhatsAppDeliveryChannel())

        result = service.deliver(DeliveryRequest(
            document_id="doc-001",
            doc_type="INVOICE",
            business_id="biz-001",
            recipient_name="John Doe",
            recipient_contact="john@example.com",
            channel="EMAIL",
        ))
    """

    def __init__(self):
        self._channels: Dict[str, DeliveryChannel] = {}
        self._delivery_log: List[DeliveryResult] = []

    def register_channel(self, channel_name: str, channel: DeliveryChannel) -> None:
        if channel_name not in VALID_CHANNELS:
            raise ValueError(f"channel_name must be one of {sorted(VALID_CHANNELS)}.")
        self._channels[channel_name] = channel

    def deliver(self, request: DeliveryRequest) -> DeliveryResult:
        """
        Deliver a document via the specified channel.

        Returns a DeliveryResult. Never raises — failed deliveries return
        a FAILED result with error_message.
        """
        channel = self._channels.get(request.channel)
        if channel is None:
            result = DeliveryResult(
                document_id=request.document_id,
                channel=request.channel,
                status="FAILED",
                error_message=f"No delivery channel registered for '{request.channel}'.",
            )
            self._delivery_log.append(result)
            logger.warning("Delivery failed: no channel '%s' registered", request.channel)
            return result

        try:
            result = channel.send(request=request)
        except Exception as exc:
            result = DeliveryResult(
                document_id=request.document_id,
                channel=request.channel,
                status="FAILED",
                error_message=str(exc),
            )
            logger.exception(
                "Delivery failed for %s via %s: %s",
                request.document_id, request.channel, exc,
            )

        self._delivery_log.append(result)
        return result

    def deliver_multi(self, request: DeliveryRequest, channels: List[str]) -> List[DeliveryResult]:
        """Deliver a document via multiple channels at once."""
        results = []
        for ch in channels:
            req = DeliveryRequest(
                document_id=request.document_id,
                doc_type=request.doc_type,
                business_id=request.business_id,
                recipient_name=request.recipient_name,
                recipient_contact=request.recipient_contact,
                channel=ch,
                render_format=request.render_format,
                subject=request.subject,
                message=request.message,
                metadata=request.metadata,
            )
            results.append(self.deliver(req))
        return results

    @property
    def delivery_log(self) -> List[DeliveryResult]:
        return list(self._delivery_log)
