import logging
from typing import Optional

from django.utils import timezone

from lounge.models import MemberProfile, MessageLog

logger = logging.getLogger(__name__)


def log_message(
    *,
    customer: Optional[MemberProfile],
    phone_number: str,
    message_type: str,
    message_body: str,
    status: str = "queued",
    provider_response: str = "",
) -> MessageLog:
    return MessageLog.objects.create(
        customer=customer,
        phone_number=phone_number,
        message_type=message_type,
        message_body=message_body,
        status=status,
        sent_at=timezone.now() if status in {"sent", "mocked"} else None,
        provider_response=provider_response,
    )


def send_sms(*, customer: Optional[MemberProfile], phone_number: str, message_type: str, message_body: str) -> MessageLog:
    logger.info("Mock SMS queued for %s: %s", phone_number, message_body)
    return log_message(
        customer=customer,
        phone_number=phone_number,
        message_type=message_type,
        message_body=message_body,
        status="mocked",
        provider_response="Mock SMS provider disabled in development.",
    )


def send_whatsapp(*, customer: Optional[MemberProfile], phone_number: str, message_type: str, message_body: str) -> MessageLog:
    logger.info("Mock WhatsApp queued for %s: %s", phone_number, message_body)
    return log_message(
        customer=customer,
        phone_number=phone_number,
        message_type=message_type,
        message_body=message_body,
        status="mocked",
        provider_response="Mock WhatsApp provider disabled in development.",
    )
