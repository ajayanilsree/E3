from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from lounge.models import (
    Booking,
    ChecklistTemplate,
    DailyChecklist,
    DailyChecklistItem,
    Event,
    Expense,
    GamingSession,
    Sale,
    Task,
    WalletLedger,
)
from lounge.roles import CUSTOMER, PARTNER, STAFF


class Command(BaseCommand):
    help = "Create demo users and sample E3 Lounge data."

    def handle(self, *args, **options):
        for role in [PARTNER, STAFF, CUSTOMER]:
            Group.objects.get_or_create(name=role)

        partner = self.user("partner", "partner123", PARTNER, is_staff=True, is_superuser=True, first_name="E3", last_name="Owner")
        staff = self.user("staff", "staff123", STAFF, is_staff=True, first_name="Shift", last_name="Lead")
        customer = self.user("customer", "customer123", CUSTOMER, first_name="Demo", last_name="Member")
        profile = customer.member_profile
        profile.phone = "9999999999"
        profile.save()

        WalletLedger.objects.get_or_create(member=profile, transaction_type="credit", amount=Decimal("1500.00"), reason="Demo top-up", reference_type="topup", created_by=partner)
        event, _ = Event.objects.get_or_create(name="Friday FIFA Cup", defaults={"description": "Casual weekly tournament.", "date": timezone.localdate() + timedelta(days=5), "time": "19:00", "entry_fee": Decimal("299.00"), "capacity": 24, "status": "open", "created_by": partner})
        Booking.objects.get_or_create(customer=profile, booking_type="gaming_station", date=timezone.localdate(), start_time="18:00", end_time="19:00", amount=Decimal("250.00"), payment_status="paid", booking_status="confirmed")
        Sale.objects.get_or_create(staff=staff, member=profile, category="beverage", item_name="Cold Coffee", quantity=1, amount=Decimal("120.00"), payment_mode="upi")
        GamingSession.objects.get_or_create(staff=staff, member=profile, station="PS5 Station 1", start_time=timezone.now() - timedelta(hours=1), end_time=timezone.now(), amount=Decimal("300.00"), payment_mode="wallet")
        Expense.objects.get_or_create(category="stock", amount=Decimal("2200.00"), description="Demo snack stock purchase", added_by=partner, date=timezone.localdate())
        Task.objects.get_or_create(title="Restock drinks fridge", assigned_to=staff, defaults={"description": "Before evening rush.", "priority": "high", "status": "todo", "due_date": timezone.localdate(), "created_by": partner})
        template, _ = ChecklistTemplate.objects.get_or_create(name="Opening Checklist", checklist_type="opening", defaults={"items": "Switch on consoles\nClean stations\nCheck QR scanner phone\nCount opening cash"})
        checklist, created = DailyChecklist.objects.get_or_create(date=timezone.localdate(), template=template, assigned_to=staff)
        if created:
            for item in template.item_list():
                DailyChecklistItem.objects.create(checklist=checklist, text=item)

        self.stdout.write(self.style.SUCCESS("Demo data ready. Logins: partner/partner123, staff/staff123, customer/customer123"))

    def user(self, username, password, role, **fields):
        user, created = User.objects.get_or_create(username=username, defaults={"email": f"{username}@e3.test", **fields})
        if created:
            user.set_password(password)
            user.save()
        group = Group.objects.get(name=role)
        user.groups.add(group)
        return user
