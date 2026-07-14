from django.contrib import admin

from .models import (
    Booking,
    BookingConfirmation,
    ChecklistTemplate,
    CustomerOTP,
    DailyChecklist,
    DailyChecklistItem,
    Event,
    EventRegistration,
    Expense,
    GamingSession,
    MemberProfile,
    MessageLog,
    Notification,
    PointTransaction,
    Receipt,
    Sale,
    ScheduledTaskLog,
    Task,
    WalletLedger,
)


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ("member_id", "user", "phone", "membership_tier", "last_login_at", "is_active", "wallet_balance", "points_balance", "created_at")
    search_fields = ("member_id", "phone", "user__username", "user__email", "user__first_name", "user__last_name")
    list_filter = ("membership_tier", "guardian_consent", "is_active", "last_login_at", "created_at")
    readonly_fields = ("otp_expires_at", "otp_resend_count", "otp_failed_attempts", "otp_last_sent_at", "last_login_at")
    actions = ("activate_customers", "deactivate_customers")

    @admin.action(description="Activate selected customers")
    def activate_customers(self, request, queryset):
        for profile in queryset.select_related("user"):
            profile.is_active = True
            profile.user.is_active = True
            profile.user.save(update_fields=["is_active"])
            profile.save(update_fields=["is_active"])

    @admin.action(description="Deactivate selected customers")
    def deactivate_customers(self, request, queryset):
        for profile in queryset.select_related("user"):
            profile.is_active = False
            profile.user.is_active = False
            profile.user.save(update_fields=["is_active"])
            profile.save(update_fields=["is_active"])


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "is_read", "created_at")
    search_fields = ("title", "message", "user__username")
    list_filter = ("is_read", "created_at")


@admin.register(CustomerOTP)
class CustomerOTPAdmin(admin.ModelAdmin):
    list_display = ("customer", "expires_at", "resend_count", "failed_attempts", "verified_at", "is_active", "created_at")
    search_fields = ("customer__member_id", "customer__phone", "customer__user__username")
    list_filter = ("is_active", "verified_at", "created_at")
    readonly_fields = ("otp_hash", "created_at", "updated_at")


@admin.register(MessageLog)
class MessageLogAdmin(admin.ModelAdmin):
    list_display = ("message_type", "customer", "phone_number", "status", "sent_at", "created_at")
    search_fields = ("phone_number", "message_body", "provider_response", "customer__member_id")
    list_filter = ("message_type", "status", "sent_at", "created_at")
    readonly_fields = ("provider_response",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("customer", "booking_type", "date", "start_time", "end_time", "amount", "payment_status", "booking_status")
    search_fields = ("customer__member_id", "customer__user__username", "customer__phone")
    list_filter = ("booking_type", "payment_status", "booking_status", "date")


@admin.register(BookingConfirmation)
class BookingConfirmationAdmin(admin.ModelAdmin):
    list_display = ("booking", "customer", "confirmed_at", "message_log")
    search_fields = ("booking__id", "customer__member_id", "customer__phone")
    list_filter = ("confirmed_at",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "date", "time", "entry_fee", "capacity", "status", "created_by")
    search_fields = ("name", "description")
    list_filter = ("status", "date")


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("event", "customer", "payment_status", "registration_status", "created_at")
    search_fields = ("event__name", "customer__member_id", "customer__user__username")
    list_filter = ("payment_status", "registration_status", "created_at")


@admin.register(WalletLedger)
class WalletLedgerAdmin(admin.ModelAdmin):
    list_display = ("member", "transaction_type", "amount", "reference_type", "created_by", "created_at")
    search_fields = ("member__member_id", "reason", "created_by__username")
    list_filter = ("transaction_type", "reference_type", "created_at")


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ("member", "points", "reason", "created_by", "created_at")
    search_fields = ("member__member_id", "reason")
    list_filter = ("created_at",)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "customer", "transaction_type", "amount", "created_at")
    search_fields = ("receipt_number", "customer__member_id", "customer__phone", "source_model", "source_id")
    list_filter = ("transaction_type", "created_at")
    readonly_fields = ("receipt_number", "created_at", "updated_at")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("item_name", "category", "quantity", "amount", "payment_mode", "staff", "member", "created_at")
    search_fields = ("item_name", "member__member_id", "staff__username")
    list_filter = ("category", "payment_mode", "created_at")


@admin.register(GamingSession)
class GamingSessionAdmin(admin.ModelAdmin):
    list_display = ("member", "station", "start_time", "end_time", "duration_minutes", "amount", "payment_mode", "staff")
    search_fields = ("member__member_id", "station", "staff__username")
    list_filter = ("payment_mode", "start_time")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("category", "amount", "date", "added_by", "reviewed")
    search_fields = ("description", "added_by__username")
    list_filter = ("category", "reviewed", "date")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "assigned_to", "priority", "status", "due_date", "created_by")
    search_fields = ("title", "description", "assigned_to__username")
    list_filter = ("priority", "status", "due_date")


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "checklist_type", "created_at")
    search_fields = ("name", "items")
    list_filter = ("checklist_type",)


class DailyChecklistItemInline(admin.TabularInline):
    model = DailyChecklistItem
    extra = 0


@admin.register(DailyChecklist)
class DailyChecklistAdmin(admin.ModelAdmin):
    list_display = ("template", "date", "assigned_to", "status")
    search_fields = ("template__name", "assigned_to__username")
    list_filter = ("status", "date", "template__checklist_type")
    inlines = [DailyChecklistItemInline]


@admin.register(ScheduledTaskLog)
class ScheduledTaskLogAdmin(admin.ModelAdmin):
    list_display = ("job_name", "frequency", "status", "started_at", "finished_at")
    search_fields = ("job_name", "details")
    list_filter = ("frequency", "status", "started_at")
    readonly_fields = ("started_at", "finished_at", "details")
