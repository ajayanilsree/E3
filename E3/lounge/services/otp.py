import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from lounge.models import CustomerOTP
from lounge.services.messaging_service import send_sms

logger = logging.getLogger(__name__)

OTP_TTL_MINUTES = 5
OTP_MAX_RESENDS = settings.OTP_MAX_RESENDS
OTP_MAX_FAILED_ATTEMPTS = settings.OTP_MAX_FAILED_ATTEMPTS
OTP_RESEND_COOLDOWN_SECONDS = settings.OTP_RESEND_COOLDOWN_SECONDS


class OTPError(Exception):
    pass


def _hash_otp(otp):
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), otp.encode("utf-8"), hashlib.sha256).hexdigest()


def _generate_otp():
    return f"{secrets.randbelow(1000000):06d}"


def get_active_otp(profile):
    return profile.otp_records.filter(is_active=True, verified_at__isnull=True).order_by("-created_at").first()


def reset_otp_limits(profile):
    profile.otp_records.filter(is_active=True).update(is_active=False)
    profile.otp_resend_count = 0
    profile.otp_failed_attempts = 0
    profile.otp_hash = ""
    profile.otp_expires_at = None
    profile.otp_last_sent_at = None
    profile.save(update_fields=["otp_resend_count", "otp_failed_attempts", "otp_hash", "otp_expires_at", "otp_last_sent_at", "updated_at"])


def send_otp(profile, *, is_resend=False):
    if not profile.is_active or not profile.user.is_active:
        raise OTPError("This customer account is inactive.")
    now = timezone.now()
    active_otp = get_active_otp(profile)
    has_active_otp = bool(active_otp and now <= active_otp.expires_at)
    resend_count = active_otp.resend_count if active_otp else 0
    if is_resend and resend_count >= OTP_MAX_RESENDS:
        raise OTPError("OTP resend limit reached. Please try again later.")
    if is_resend and active_otp:
        seconds_since_last_send = (now - active_otp.last_sent_at).total_seconds()
        if seconds_since_last_send < OTP_RESEND_COOLDOWN_SECONDS:
            raise OTPError("Please wait before requesting another OTP.")
    if not is_resend and has_active_otp and resend_count >= OTP_MAX_RESENDS:
        raise OTPError("OTP request limit reached. Please try again after the current OTP expires.")

    otp = _generate_otp()
    if active_otp and active_otp.is_active:
        active_otp.is_active = False
        active_otp.save(update_fields=["is_active", "updated_at"])
    next_resend_count = resend_count + 1 if is_resend else (resend_count if has_active_otp else 0)
    otp_record = CustomerOTP.objects.create(
        customer=profile,
        otp_hash=_hash_otp(otp),
        expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
        resend_count=next_resend_count,
        failed_attempts=0,
        last_sent_at=now,
    )
    profile.otp_hash = _hash_otp(otp)
    profile.otp_expires_at = otp_record.expires_at
    profile.otp_failed_attempts = 0
    profile.otp_resend_count = next_resend_count
    profile.otp_last_sent_at = now
    profile.save(update_fields=["otp_hash", "otp_expires_at", "otp_failed_attempts", "otp_resend_count", "otp_last_sent_at", "updated_at"])
    dispatch_otp_sms(profile, otp)


def verify_otp(profile, otp):
    if not profile.is_active or not profile.user.is_active:
        raise OTPError("This customer account is inactive.")
    otp_record = get_active_otp(profile)
    if not otp_record:
        raise OTPError("Please request a new OTP.")
    if otp_record.failed_attempts >= OTP_MAX_FAILED_ATTEMPTS:
        raise OTPError("Too many incorrect attempts. Please request a new OTP.")
    if timezone.now() > otp_record.expires_at:
        otp_record.is_active = False
        otp_record.save(update_fields=["is_active", "updated_at"])
        raise OTPError("OTP expired. Please request a new OTP.")
    if not hmac.compare_digest(otp_record.otp_hash, _hash_otp(otp)):
        otp_record.failed_attempts += 1
        otp_record.save(update_fields=["failed_attempts", "updated_at"])
        profile.otp_failed_attempts = otp_record.failed_attempts
        profile.save(update_fields=["otp_failed_attempts", "updated_at"])
        raise OTPError("Incorrect OTP. Please try again.")

    otp_record.verified_at = timezone.now()
    otp_record.is_active = False
    otp_record.save(update_fields=["verified_at", "is_active", "updated_at"])
    profile.otp_hash = ""
    profile.otp_expires_at = None
    profile.otp_resend_count = 0
    profile.otp_failed_attempts = 0
    profile.last_login_at = timezone.now()
    profile.save(update_fields=["otp_hash", "otp_expires_at", "otp_resend_count", "otp_failed_attempts", "last_login_at", "updated_at"])


def dispatch_otp_sms(profile, otp):
    phone = profile.phone or ""
    logger.warning("E3 Lounge OTP for %s is %s", phone, otp)
    send_sms(customer=profile, phone_number=phone, message_type="otp", message_body=f"Your E3 Lounge OTP is {otp}. It expires in 5 minutes.")
    provider = settings.SMS_PROVIDER.lower()
    if provider == "console":
        return
    # Provider credentials are intentionally read from environment variables here
    # so Twilio, MSG91, Fast2SMS, or WhatsApp Cloud API can be plugged in later.
    api_key = settings.SMS_API_KEY
    api_secret = settings.SMS_API_SECRET
    sender_id = settings.SMS_SENDER_ID
    if not api_key:
        logger.warning("SMS_PROVIDER=%s is configured without SMS_API_KEY. OTP for %s was not sent.", provider, phone)
        return
    logger.info("OTP dispatch requested through %s for %s using sender %s and secret configured=%s", provider, phone, sender_id, bool(api_secret))
