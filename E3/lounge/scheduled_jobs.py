import logging

from django.utils import timezone

from .models import ScheduledTaskLog

logger = logging.getLogger(__name__)


def _run_placeholder(job_name: str, frequency: str) -> ScheduledTaskLog:
    log = ScheduledTaskLog.objects.create(job_name=job_name, frequency=frequency, status="started")
    log.status = "skipped"
    log.finished_at = timezone.now()
    log.details = "Placeholder only. Campaign/report logic will be added in later phases."
    log.save(update_fields=["status", "finished_at", "details", "updated_at"])
    logger.info("Scheduled placeholder skipped: %s", job_name)
    return log


def run_daily_jobs() -> list[ScheduledTaskLog]:
    return [
        _run_placeholder("birthday_offers", "daily"),
        _run_placeholder("win_back_campaigns", "daily"),
        _run_placeholder("slot_reminders", "daily"),
        _run_placeholder("daily_reports", "daily"),
    ]


def run_weekly_jobs() -> list[ScheduledTaskLog]:
    return [_run_placeholder("founder_weekly_digest", "weekly")]


def run_monthly_jobs() -> list[ScheduledTaskLog]:
    return [_run_placeholder("monthly_reports", "monthly")]


def run_all_scheduled_jobs() -> list[ScheduledTaskLog]:
    return [*run_daily_jobs(), *run_weekly_jobs(), *run_monthly_jobs()]
