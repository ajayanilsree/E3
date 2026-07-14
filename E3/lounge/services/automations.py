import logging

from django.db import transaction

from lounge.models import Booking, BookingConfirmation, MemberProfile, Notification
from lounge.services.messaging_service import send_whatsapp
from lounge.services.receipts import create_receipt

logger = logging.getLogger(__name__)

WELCOME_MESSAGE = "Welcome to E3 Lounge. Your membership account is now active."
BOOKING_CONFIRMATION_MESSAGE = "Your booking at E3 Lounge has been confirmed."


@transaction.atomic
def trigger_welcome_message(customer: MemberProfile) -> None:
    Notification.objects.get_or_create(
        user=customer.user,
        title="Welcome to E3 Lounge",
        defaults={"message": WELCOME_MESSAGE},
    )
    send_whatsapp(
        customer=customer,
        phone_number=customer.phone or "",
        message_type="welcome",
        message_body=WELCOME_MESSAGE,
    )
    logger.info("Welcome automation queued for %s", customer.member_id)


@transaction.atomic
def trigger_booking_confirmation(booking: Booking) -> BookingConfirmation:
    Notification.objects.get_or_create(
        user=booking.customer.user,
        title="Booking confirmed",
        defaults={"message": BOOKING_CONFIRMATION_MESSAGE},
    )
    message_log = send_whatsapp(
        customer=booking.customer,
        phone_number=booking.customer.phone or "",
        message_type="booking_confirmation",
        message_body=BOOKING_CONFIRMATION_MESSAGE,
    )
    confirmation, created = BookingConfirmation.objects.get_or_create(
        booking=booking,
        defaults={"customer": booking.customer, "message_log": message_log},
    )
    if not created and not confirmation.message_log:
        confirmation.message_log = message_log
        confirmation.save(update_fields=["message_log", "updated_at"])
    create_receipt(
        customer=booking.customer,
        transaction_type="booking",
        amount=booking.amount,
        source_model="Booking",
        source_id=booking.id,
    )
    logger.info("Booking confirmation automation completed for booking #%s", booking.id)
    return confirmation
