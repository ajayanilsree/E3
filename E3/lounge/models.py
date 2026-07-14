from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class MemberProfile(TimeStampedModel):
    TIER_CHOICES = [
        ("bronze", "Bronze"),
        ("silver", "Silver"),
        ("gold", "Gold"),
        ("platinum", "Platinum"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="member_profile")
    member_id = models.CharField(max_length=20, unique=True, blank=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    membership_tier = models.CharField(max_length=20, choices=TIER_CHOICES, default="bronze")
    guardian_consent = models.BooleanField(default=False)
    otp_hash = models.CharField(max_length=128, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_resend_count = models.PositiveSmallIntegerField(default=0)
    otp_failed_attempts = models.PositiveSmallIntegerField(default=0)
    otp_last_sent_at = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.member_id:
            with transaction.atomic():
                last = MemberProfile.objects.select_for_update().exclude(member_id="").order_by("-id").first()
                next_number = 1001 if not last else 1001 + last.id
                self.member_id = f"E3-{next_number}"
        super().save(*args, **kwargs)

    @property
    def wallet_balance(self):
        credits = self.wallet_entries.filter(transaction_type__in=["credit", "adjustment"], amount__gt=0).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        debits = self.wallet_entries.filter(transaction_type="debit").aggregate(total=Sum("amount"))["total"] or Decimal("0")
        negative_adjustments = self.wallet_entries.filter(transaction_type="adjustment", amount__lt=0).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        return credits - debits + negative_adjustments

    @property
    def points_balance(self):
        return self.point_entries.aggregate(total=Sum("points"))["total"] or 0

    def __str__(self):
        return f"{self.member_id} - {self.user.get_full_name() or self.user.username}"


class CustomerOTP(TimeStampedModel):
    customer = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name="otp_records")
    otp_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    resend_count = models.PositiveSmallIntegerField(default=0)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    last_sent_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP for {self.customer.member_id} - {'active' if self.is_active else 'closed'}"


class Notification(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=120)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.title} -> {self.user.username}"


class MessageLog(TimeStampedModel):
    TYPE_CHOICES = [
        ("otp", "OTP"),
        ("welcome", "Welcome"),
        ("booking_confirmation", "Booking Confirmation"),
        ("receipt", "Receipt"),
        ("general", "General"),
    ]
    STATUS_CHOICES = [("queued", "Queued"), ("sent", "Sent"), ("failed", "Failed"), ("mocked", "Mocked")]

    customer = models.ForeignKey(MemberProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="message_logs")
    phone_number = models.CharField(max_length=20)
    message_type = models.CharField(max_length=40, choices=TYPE_CHOICES)
    message_body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    sent_at = models.DateTimeField(null=True, blank=True)
    provider_response = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_message_type_display()} -> {self.phone_number}"


class Booking(TimeStampedModel):
    BOOKING_TYPES = [
        ("gaming_station", "Gaming Station"),
        ("suite", "Suite"),
        ("table", "Table"),
        ("party", "Party"),
    ]
    PAYMENT_STATUS = [("unpaid", "Unpaid"), ("paid", "Paid"), ("refunded", "Refunded")]
    BOOKING_STATUS = [("pending", "Pending"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled"), ("completed", "Completed")]

    customer = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name="bookings")
    booking_type = models.CharField(max_length=30, choices=BOOKING_TYPES)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default="unpaid")
    booking_status = models.CharField(max_length=20, choices=BOOKING_STATUS, default="pending")
    revenue_logged = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date", "-start_time"]

    def __str__(self):
        return f"{self.customer.member_id} {self.get_booking_type_display()} {self.date}"


class BookingConfirmation(TimeStampedModel):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="confirmation")
    customer = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name="booking_confirmations")
    message_log = models.ForeignKey(MessageLog, on_delete=models.SET_NULL, null=True, blank=True, related_name="booking_confirmations")
    confirmed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-confirmed_at"]

    def __str__(self):
        return f"Confirmation for booking #{self.booking_id}"


class Event(TimeStampedModel):
    STATUS_CHOICES = [("draft", "Draft"), ("open", "Open"), ("full", "Full"), ("closed", "Closed"), ("completed", "Completed")]

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    date = models.DateField()
    time = models.TimeField()
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    capacity = models.PositiveIntegerField(default=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_events")

    @property
    def seats_left(self):
        confirmed = self.registrations.exclude(registration_status="cancelled").count()
        return max(self.capacity - confirmed, 0)

    def __str__(self):
        return self.name


class EventRegistration(TimeStampedModel):
    PAYMENT_STATUS = Booking.PAYMENT_STATUS
    REGISTRATION_STATUS = [("pending", "Pending"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled"), ("waitlisted", "Waitlisted")]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    customer = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name="event_registrations")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default="unpaid")
    registration_status = models.CharField(max_length=20, choices=REGISTRATION_STATUS, default="confirmed")
    revenue_logged = models.BooleanField(default=False)

    class Meta:
        unique_together = ("event", "customer")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.member_id} -> {self.event.name}"


class WalletLedger(TimeStampedModel):
    TRANSACTION_TYPES = [("credit", "Credit"), ("debit", "Debit"), ("adjustment", "Adjustment")]
    REFERENCE_TYPES = [("topup", "Top-up"), ("sale", "Sale"), ("session", "Session"), ("event", "Event"), ("booking", "Booking"), ("manual", "Manual")]

    member = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name="wallet_entries")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255)
    reference_type = models.CharField(max_length=20, choices=REFERENCE_TYPES, default="manual")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.member.member_id} {self.transaction_type} {self.amount}"


class PointTransaction(TimeStampedModel):
    member = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name="point_entries")
    points = models.IntegerField()
    reason = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.member.member_id} {self.points}"


class Receipt(TimeStampedModel):
    TRANSACTION_TYPES = [
        ("sale", "Sale"),
        ("session", "Gaming Session"),
        ("booking", "Booking"),
    ]

    receipt_number = models.CharField(max_length=30, unique=True, blank=True)
    customer = models.ForeignKey(MemberProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="receipts")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    source_model = models.CharField(max_length=40, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("source_model", "source_id", "transaction_type")

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            with transaction.atomic():
                last = Receipt.objects.select_for_update().exclude(receipt_number="").order_by("-id").first()
                next_number = 1 if not last else last.id + 1
                self.receipt_number = f"E3R-{timezone.localdate():%Y%m%d}-{next_number:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.receipt_number


class Sale(TimeStampedModel):
    CATEGORY_CHOICES = [("food", "Food"), ("beverage", "Beverage"), ("other", "Other")]
    PAYMENT_MODES = [("cash", "Cash"), ("upi", "UPI"), ("wallet", "Wallet"), ("card", "Card")]

    staff = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="sales")
    member = models.ForeignKey(MemberProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    item_name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.item_name} {self.amount}"


class GamingSession(TimeStampedModel):
    PAYMENT_MODES = Sale.PAYMENT_MODES

    staff = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="gaming_sessions")
    member = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name="gaming_sessions")
    station = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES)

    @property
    def duration_minutes(self):
        return max(int((self.end_time - self.start_time).total_seconds() // 60), 0)

    class Meta:
        ordering = ["-start_time"]

    def __str__(self):
        return f"{self.member.member_id} {self.station}"


class Expense(TimeStampedModel):
    CATEGORY_CHOICES = [
        ("rent", "Rent"),
        ("salary", "Salary"),
        ("stock", "Stock"),
        ("utility", "Utility"),
        ("marketing", "Marketing"),
        ("maintenance", "Maintenance"),
        ("other", "Other"),
    ]

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.TextField()
    receipt = models.FileField(upload_to="receipts/", blank=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="expenses")
    date = models.DateField(default=timezone.localdate)
    reviewed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_category_display()} {self.amount}"


class Task(TimeStampedModel):
    PRIORITY_CHOICES = [("low", "Low"), ("medium", "Medium"), ("high", "High")]
    STATUS_CHOICES = [("todo", "To Do"), ("doing", "Doing"), ("done", "Done")]

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assigned_tasks")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="todo")
    due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_tasks")

    class Meta:
        ordering = ["status", "due_date", "-created_at"]

    def __str__(self):
        return self.title


class ChecklistTemplate(TimeStampedModel):
    TYPE_CHOICES = [("opening", "Opening"), ("closing", "Closing"), ("cleaning", "Cleaning"), ("restock", "Restock")]

    name = models.CharField(max_length=120)
    checklist_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    items = models.TextField(help_text="One checklist item per line.")

    def item_list(self):
        return [item.strip() for item in self.items.splitlines() if item.strip()]

    def __str__(self):
        return self.name


class DailyChecklist(TimeStampedModel):
    STATUS_CHOICES = [("todo", "To Do"), ("doing", "Doing"), ("done", "Done")]

    date = models.DateField(default=timezone.localdate)
    template = models.ForeignKey(ChecklistTemplate, on_delete=models.CASCADE, related_name="daily_checklists")
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_checklists")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="todo")

    class Meta:
        unique_together = ("date", "template", "assigned_to")
        ordering = ["-date", "template__name"]

    def __str__(self):
        return f"{self.template.name} {self.date}"


class DailyChecklistItem(TimeStampedModel):
    checklist = models.ForeignKey(DailyChecklist, on_delete=models.CASCADE, related_name="items")
    text = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.text


class ScheduledTaskLog(TimeStampedModel):
    FREQUENCY_CHOICES = [("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")]
    STATUS_CHOICES = [("started", "Started"), ("completed", "Completed"), ("failed", "Failed"), ("skipped", "Skipped")]

    job_name = models.CharField(max_length=120)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.job_name} - {self.status}"
