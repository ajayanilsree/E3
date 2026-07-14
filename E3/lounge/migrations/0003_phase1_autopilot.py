# Generated manually for E3 Lounge Phase 1 autopilot models.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lounge", "0002_customer_phone_otp"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerOTP",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("otp_hash", models.CharField(max_length=128)),
                ("expires_at", models.DateTimeField()),
                ("resend_count", models.PositiveSmallIntegerField(default=0)),
                ("failed_attempts", models.PositiveSmallIntegerField(default=0)),
                ("last_sent_at", models.DateTimeField()),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="otp_records", to="lounge.memberprofile")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="MessageLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("phone_number", models.CharField(max_length=20)),
                ("message_type", models.CharField(choices=[("otp", "OTP"), ("welcome", "Welcome"), ("booking_confirmation", "Booking Confirmation"), ("receipt", "Receipt"), ("general", "General")], max_length=40)),
                ("message_body", models.TextField()),
                ("status", models.CharField(choices=[("queued", "Queued"), ("sent", "Sent"), ("failed", "Failed"), ("mocked", "Mocked")], default="queued", max_length=20)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("provider_response", models.TextField(blank=True)),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="message_logs", to="lounge.memberprofile")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Receipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("receipt_number", models.CharField(blank=True, max_length=30, unique=True)),
                ("transaction_type", models.CharField(choices=[("sale", "Sale"), ("session", "Gaming Session"), ("booking", "Booking")], max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("source_model", models.CharField(blank=True, max_length=40)),
                ("source_id", models.PositiveIntegerField(blank=True, null=True)),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="receipts", to="lounge.memberprofile")),
            ],
            options={"ordering": ["-created_at"], "unique_together": {("source_model", "source_id", "transaction_type")}},
        ),
        migrations.CreateModel(
            name="ScheduledTaskLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("job_name", models.CharField(max_length=120)),
                ("frequency", models.CharField(choices=[("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")], max_length=20)),
                ("status", models.CharField(choices=[("started", "Started"), ("completed", "Completed"), ("failed", "Failed"), ("skipped", "Skipped")], max_length=20)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("details", models.TextField(blank=True)),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="BookingConfirmation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("confirmed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("booking", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="confirmation", to="lounge.booking")),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="booking_confirmations", to="lounge.memberprofile")),
                ("message_log", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="booking_confirmations", to="lounge.messagelog")),
            ],
            options={"ordering": ["-confirmed_at"]},
        ),
    ]
