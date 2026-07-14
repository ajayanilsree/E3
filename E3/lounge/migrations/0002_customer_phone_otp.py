# Generated manually for customer phone + OTP authentication.

from django.db import migrations, models


def blank_phones_to_null(apps, schema_editor):
    MemberProfile = apps.get_model("lounge", "MemberProfile")
    MemberProfile.objects.filter(phone="").update(phone=None)


class Migration(migrations.Migration):

    dependencies = [
        ("lounge", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(blank_phones_to_null, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="memberprofile",
            name="phone",
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="memberprofile",
            name="otp_hash",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="memberprofile",
            name="otp_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="memberprofile",
            name="otp_resend_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="memberprofile",
            name="otp_failed_attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="memberprofile",
            name="otp_last_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="memberprofile",
            name="last_login_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="memberprofile",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
