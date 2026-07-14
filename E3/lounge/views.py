import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    BookingForm,
    BookingStatusForm,
    ChecklistTemplateForm,
    CustomerOTPVerificationForm,
    CustomerPasswordLoginForm,
    CustomerRegistrationForm,
    DailyChecklistForm,
    EventForm,
    EventRegistrationStatusForm,
    ExpenseForm,
    GamingSessionForm,
    MemberLookupForm,
    PointTransactionForm,
    SaleForm,
    StaffUserForm,
    TaskForm,
    TaskStatusForm,
    WalletLedgerForm,
)
from .models import (
    Booking,
    ChecklistTemplate,
    DailyChecklist,
    DailyChecklistItem,
    Event,
    EventRegistration,
    Expense,
    GamingSession,
    MemberProfile,
    Notification,
    PointTransaction,
    Receipt,
    Sale,
    Task,
    WalletLedger,
)
from .roles import CUSTOMER, PARTNER, STAFF, has_role, role_home, role_required
from .services.automations import trigger_booking_confirmation, trigger_welcome_message
from .services.otp import OTPError, get_active_otp, send_otp, verify_otp
from .services.points import award_points
from .services.receipts import build_receipt_pdf, create_receipt


def money_total(queryset):
    return queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0")


def home(request):
    return render(request, "home.html")


def register(request):
    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                send_otp(user.member_profile)
                request.session["pending_customer_profile_id"] = user.member_profile.id
                request.session["pending_customer_signup"] = True
            messages.success(request, "Account created. We sent an OTP to your phone number.")
            return redirect("customer_verify_otp")
    else:
        form = CustomerRegistrationForm()
    return render(request, "registration/register.html", {"form": form})


def customer_login(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = CustomerPasswordLoginForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data["username"].strip()
            password = form.cleaned_data["password"]
            username = username_or_email
            if "@" in username_or_email:
                user_match = User.objects.filter(email__iexact=username_or_email).first()
                if user_match:
                    username = user_match.username

            user = authenticate(request, username=username, password=password)
            if user is None:
                messages.error(request, "Invalid username/email or password.")
            else:
                login(request, user)
                messages.success(request, "Welcome back.")
                return redirect("dashboard")
    else:
        form = CustomerPasswordLoginForm()
    return render(request, "registration/customer_login.html", {"form": form})


def customer_verify_otp(request):
    profile_id = request.session.get("pending_customer_profile_id")
    if not profile_id:
        messages.error(request, "Please enter your phone number to continue.")
        return redirect("customer_login")
    profile = get_object_or_404(MemberProfile.objects.select_related("user"), pk=profile_id)
    if request.method == "POST":
        form = CustomerOTPVerificationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    verify_otp(profile, form.cleaned_data["otp"])
                    is_first_signup = bool(request.session.get("pending_customer_signup"))
                    if is_first_signup:
                        trigger_welcome_message(profile)
            except OTPError as error:
                messages.error(request, str(error))
            else:
                login(request, profile.user)
                request.session.pop("pending_customer_profile_id", None)
                request.session.pop("pending_customer_signup", None)
                messages.success(request, "You are logged in.")
                return redirect("customer_dashboard")
    else:
        form = CustomerOTPVerificationForm()
    seconds_remaining = 0
    active_otp = get_active_otp(profile)
    if active_otp:
        seconds_remaining = max(int((active_otp.expires_at - timezone.now()).total_seconds()), 0)
    return render(
        request,
        "registration/verify_otp.html",
        {
            "form": form,
            "phone": profile.phone,
            "seconds_remaining": seconds_remaining,
        },
    )


def customer_resend_otp(request):
    profile_id = request.session.get("pending_customer_profile_id")
    if not profile_id:
        messages.error(request, "Please enter your phone number to continue.")
        return redirect("customer_login")
    profile = get_object_or_404(MemberProfile.objects.select_related("user"), pk=profile_id)
    if request.method == "POST":
        try:
            send_otp(profile, is_resend=True)
            messages.success(request, "A new OTP has been sent.")
        except OTPError as error:
            messages.error(request, str(error))
    return redirect("customer_verify_otp")


@login_required
def dashboard(request):
    return redirect(role_home(request.user))


@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return redirect(request.META.get("HTTP_REFERER", "dashboard"))


@role_required(CUSTOMER)
def customer_dashboard(request):
    profile = request.user.member_profile
    try:
        import qrcode
        import qrcode.image.svg
        from io import BytesIO

        image = qrcode.make(profile.member_id, image_factory=qrcode.image.svg.SvgPathImage)
        buffer = BytesIO()
        image.save(buffer)
        qr_svg = buffer.getvalue().decode("utf-8")
    except Exception:
        qr_svg = f"<div class='qr-fallback'>{profile.member_id}</div>"
    context = {
        "profile": profile,
        "bookings": profile.bookings.all()[:6],
        "registrations": profile.event_registrations.select_related("event")[:6],
        "wallet_entries": profile.wallet_entries.all()[:8],
        "point_entries": profile.point_entries.all()[:8],
        "receipts": profile.receipts.all()[:8],
        "qr_svg": qr_svg,
    }
    return render(request, "customer/dashboard.html", context)


@role_required(CUSTOMER)
def customer_booking_create(request):
    profile = request.user.member_profile
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.customer = profile
            booking.save()
            Notification.objects.create(user=request.user, title="Booking received", message="Your booking is pending confirmation.")
            messages.success(request, "Booking request created.")
            return redirect("customer_dashboard")
    else:
        form = BookingForm()
    return render(request, "shared/form_page.html", {"title": "Book a Slot", "form": form})


@role_required(CUSTOMER)
def customer_events(request):
    events = Event.objects.filter(status="open", date__gte=timezone.localdate()).order_by("date", "time")
    return render(request, "customer/events.html", {"events": events})


@role_required(CUSTOMER)
def customer_event_register(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    profile = request.user.member_profile
    if event.status != "open" or event.seats_left <= 0:
        messages.error(request, "This event is no longer accepting registrations.")
        return redirect("customer_events")
    try:
        EventRegistration.objects.create(event=event, customer=profile)
        Notification.objects.create(user=request.user, title="Event registration confirmed", message=f"You are registered for {event.name}.")
        messages.success(request, "Event registration confirmed.")
    except IntegrityError:
        messages.info(request, "You are already registered for this event.")
    if event.seats_left <= 0:
        event.status = "full"
        event.save(update_fields=["status"])
    return redirect("customer_events")


@role_required(STAFF, PARTNER)
def staff_dashboard(request):
    today = timezone.localdate()
    staff_tasks = Task.objects.filter(assigned_to=request.user)
    checklists = DailyChecklist.objects.filter(assigned_to=request.user, date=today).prefetch_related("items")
    context = {
        "tasks": staff_tasks,
        "checklists": checklists,
        "today_bookings": Booking.objects.filter(date=today).select_related("customer"),
        "today_events": Event.objects.filter(date=today),
    }
    return render(request, "staff/dashboard.html", context)


@role_required(STAFF, PARTNER)
def member_lookup(request):
    form = MemberLookupForm(request.GET or None)
    members = MemberProfile.objects.none()
    if form.is_valid():
        query = form.cleaned_data["query"]
        members = MemberProfile.objects.filter(
            Q(member_id__icontains=query)
            | Q(phone__icontains=query)
            | Q(user__email__icontains=query)
            | Q(user__username__icontains=query)
        )
    return render(request, "staff/member_lookup.html", {"form": form, "members": members})


@role_required(STAFF, PARTNER)
def sale_create(request):
    if request.method == "POST":
        form = SaleForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                sale = form.save(commit=False)
                sale.staff = request.user
                sale.save()
                if sale.payment_mode == "wallet" and sale.member:
                    WalletLedger.objects.create(member=sale.member, transaction_type="debit", amount=sale.amount, reason=f"Sale: {sale.item_name}", reference_type="sale", created_by=request.user)
                award_points(member=sale.member, amount=sale.amount, reason=f"Auto earn from sale #{sale.id}: {sale.item_name}", created_by=request.user)
                create_receipt(customer=sale.member, transaction_type="sale", amount=sale.amount, source_model="Sale", source_id=sale.id)
            messages.success(request, "Sale logged.")
            return redirect("staff_dashboard")
    else:
        form = SaleForm()
    return render(request, "shared/form_page.html", {"title": "Log F&B Sale", "form": form})


@role_required(STAFF, PARTNER)
def session_create(request):
    if request.method == "POST":
        form = GamingSessionForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                session = form.save(commit=False)
                session.staff = request.user
                session.save()
                if session.payment_mode == "wallet":
                    WalletLedger.objects.create(member=session.member, transaction_type="debit", amount=session.amount, reason=f"Gaming session: {session.station}", reference_type="session", created_by=request.user)
                award_points(member=session.member, amount=session.amount, reason=f"Auto earn from session #{session.id}: {session.station}", created_by=request.user)
                create_receipt(customer=session.member, transaction_type="session", amount=session.amount, source_model="GamingSession", source_id=session.id)
            messages.success(request, "Gaming session logged.")
            return redirect("staff_dashboard")
    else:
        form = GamingSessionForm()
    return render(request, "shared/form_page.html", {"title": "Log Gaming Session", "form": form})


@role_required(STAFF, PARTNER)
def task_status_update(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    if task.assigned_to != request.user and not has_role(request.user, PARTNER):
        messages.error(request, "You can only update tasks assigned to you.")
        return redirect("staff_dashboard")
    if request.method == "POST":
        form = TaskStatusForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, "Task status updated.")
    return redirect(request.META.get("HTTP_REFERER", "staff_dashboard"))


@role_required(STAFF, PARTNER)
def checklist_item_toggle(request, item_id):
    item = get_object_or_404(DailyChecklistItem, pk=item_id)
    if item.checklist.assigned_to != request.user and not has_role(request.user, PARTNER):
        messages.error(request, "You can only update your assigned checklist.")
        return redirect("staff_dashboard")
    item.completed = not item.completed
    item.completed_by = request.user if item.completed else None
    item.completed_at = timezone.now() if item.completed else None
    item.save()
    checklist = item.checklist
    checklist.status = "done" if checklist.items.filter(completed=False).count() == 0 else "doing"
    checklist.save(update_fields=["status"])
    return redirect(request.META.get("HTTP_REFERER", "staff_dashboard"))


@role_required(PARTNER)
def partner_dashboard(request):
    today = timezone.localdate()
    context = {
        "today_revenue": money_total(Sale.objects.filter(created_at__date=today)) + money_total(GamingSession.objects.filter(created_at__date=today)) + money_total(Booking.objects.filter(date=today, payment_status="paid")),
        "member_count": MemberProfile.objects.count(),
        "booking_count": Booking.objects.count(),
        "event_count": Event.objects.count(),
        "sales": Sale.objects.all()[:6],
        "sessions": GamingSession.objects.select_related("member")[:6],
        "expenses": Expense.objects.all()[:6],
        "tasks": Task.objects.select_related("assigned_to")[:8],
    }
    return render(request, "partner/dashboard.html", context)


@role_required(PARTNER, STAFF)
def manage_bookings(request):
    bookings = Booking.objects.select_related("customer", "customer__user")
    return render(request, "partner/bookings.html", {"bookings": bookings})


@role_required(PARTNER, STAFF)
def booking_status_update(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    if request.method == "POST":
        form = BookingStatusForm(request.POST, instance=booking)
        if form.is_valid():
            with transaction.atomic():
                previous_payment_status = booking.payment_status
                booking = form.save()
                if booking.payment_status == "paid" and previous_payment_status != "paid":
                    trigger_booking_confirmation(booking)
                if booking.payment_status == "paid" and not booking.revenue_logged:
                    booking.revenue_logged = True
                    booking.save(update_fields=["revenue_logged"])
            messages.success(request, "Booking updated.")
    return redirect("manage_bookings")


@login_required
def receipt_download(request, receipt_id):
    receipt = get_object_or_404(Receipt.objects.select_related("customer", "customer__user"), pk=receipt_id)
    if not has_role(request.user, PARTNER, STAFF):
        if not receipt.customer or receipt.customer.user_id != request.user.id:
            raise Http404
    response = HttpResponse(build_receipt_pdf(receipt), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{receipt.receipt_number}.pdf"'
    return response


@role_required(PARTNER, STAFF)
def manage_events(request):
    events = Event.objects.order_by("-date")
    return render(request, "partner/events.html", {"events": events})


@role_required(PARTNER)
def event_create(request):
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            messages.success(request, "Event created.")
            return redirect("manage_events")
    else:
        form = EventForm()
    return render(request, "shared/form_page.html", {"title": "Create Event", "form": form})


@role_required(PARTNER, STAFF)
def manage_event_registrations(request):
    registrations = EventRegistration.objects.select_related("event", "customer", "customer__user")
    return render(request, "partner/event_registrations.html", {"registrations": registrations})


@role_required(PARTNER, STAFF)
def event_registration_update(request, registration_id):
    registration = get_object_or_404(EventRegistration, pk=registration_id)
    if request.method == "POST":
        form = EventRegistrationStatusForm(request.POST, instance=registration)
        if form.is_valid():
            registration = form.save()
            if registration.payment_status == "paid" and not registration.revenue_logged:
                registration.revenue_logged = True
                registration.save(update_fields=["revenue_logged"])
            messages.success(request, "Registration updated.")
    return redirect("manage_event_registrations")


@role_required(PARTNER)
def manage_tasks(request):
    return render(request, "partner/tasks.html", {"tasks": Task.objects.select_related("assigned_to", "created_by")})


@role_required(PARTNER)
def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            Notification.objects.create(user=task.assigned_to, title="New task assigned", message=task.title)
            messages.success(request, "Task assigned.")
            return redirect("manage_tasks")
    else:
        form = TaskForm()
    return render(request, "shared/form_page.html", {"title": "Assign Task", "form": form})


@role_required(PARTNER)
def manage_checklists(request):
    return render(request, "partner/checklists.html", {"templates": ChecklistTemplate.objects.all(), "checklists": DailyChecklist.objects.prefetch_related("items")})


@role_required(PARTNER)
def checklist_template_create(request):
    if request.method == "POST":
        form = ChecklistTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Checklist template created.")
            return redirect("manage_checklists")
    else:
        form = ChecklistTemplateForm()
    return render(request, "shared/form_page.html", {"title": "Create Checklist Template", "form": form})


@role_required(PARTNER)
def daily_checklist_generate(request):
    if request.method == "POST":
        form = DailyChecklistForm(request.POST)
        if form.is_valid():
            checklist = form.save()
            for text in checklist.template.item_list():
                DailyChecklistItem.objects.create(checklist=checklist, text=text)
            messages.success(request, "Daily checklist generated.")
            return redirect("manage_checklists")
    else:
        form = DailyChecklistForm(initial={"date": timezone.localdate()})
    return render(request, "shared/form_page.html", {"title": "Generate Daily Checklist", "form": form})


@role_required(PARTNER)
def manage_expenses(request):
    return render(request, "partner/expenses.html", {"expenses": Expense.objects.select_related("added_by")})


@role_required(PARTNER)
def expense_create(request):
    if request.method == "POST":
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.added_by = request.user
            expense.save()
            messages.success(request, "Expense saved.")
            return redirect("manage_expenses")
    else:
        form = ExpenseForm()
    return render(request, "shared/form_page.html", {"title": "Add Expense", "form": form})


@role_required(PARTNER)
def wallet_ledger(request):
    return render(request, "partner/wallet.html", {"entries": WalletLedger.objects.select_related("member", "created_by")})


@role_required(PARTNER, STAFF)
def wallet_entry_create(request):
    if request.method == "POST":
        form = WalletLedgerForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.created_by = request.user
            entry.save()
            messages.success(request, "Wallet ledger entry recorded.")
            return redirect("wallet_ledger" if has_role(request.user, PARTNER) else "staff_dashboard")
    else:
        form = WalletLedgerForm()
    return render(request, "shared/form_page.html", {"title": "Wallet Ledger Entry", "form": form})


@role_required(PARTNER, STAFF)
def point_entry_create(request):
    if request.method == "POST":
        form = PointTransactionForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.created_by = request.user
            entry.save()
            messages.success(request, "Point transaction recorded.")
            return redirect("partner_dashboard" if has_role(request.user, PARTNER) else "staff_dashboard")
    else:
        form = PointTransactionForm()
    return render(request, "shared/form_page.html", {"title": "Point Transaction", "form": form})


@role_required(PARTNER)
def manage_staff(request):
    staff = User.objects.filter(groups__name=STAFF).order_by("first_name", "username")
    return render(request, "partner/staff.html", {"staff": staff})


@role_required(PARTNER)
def staff_create(request):
    if request.method == "POST":
        form = StaffUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff account created.")
            return redirect("manage_staff")
    else:
        form = StaffUserForm()
    return render(request, "shared/form_page.html", {"title": "Create Staff Account", "form": form})


@role_required(PARTNER)
def accounting_tracker(request):
    start = request.GET.get("start")
    end = request.GET.get("end")
    sales = Sale.objects.all()
    sessions = GamingSession.objects.all()
    expenses = Expense.objects.all()
    bookings = Booking.objects.filter(payment_status="paid")
    registrations = EventRegistration.objects.filter(payment_status="paid")
    if start:
        sales = sales.filter(created_at__date__gte=start)
        sessions = sessions.filter(created_at__date__gte=start)
        expenses = expenses.filter(date__gte=start)
        bookings = bookings.filter(date__gte=start)
        registrations = registrations.filter(created_at__date__gte=start)
    if end:
        sales = sales.filter(created_at__date__lte=end)
        sessions = sessions.filter(created_at__date__lte=end)
        expenses = expenses.filter(date__lte=end)
        bookings = bookings.filter(date__lte=end)
        registrations = registrations.filter(created_at__date__lte=end)
    sales_revenue = money_total(sales)
    session_revenue = money_total(sessions)
    booking_revenue = money_total(bookings)
    event_revenue = sum((r.event.entry_fee for r in registrations), Decimal("0"))
    total_expenses = money_total(expenses)
    wallet_liability = sum((m.wallet_balance for m in MemberProfile.objects.all()), Decimal("0"))
    payment_split = {mode: money_total(sales.filter(payment_mode=mode)) + money_total(sessions.filter(payment_mode=mode)) for mode, _ in Sale.PAYMENT_MODES}
    context = {
        "sales_revenue": sales_revenue,
        "session_revenue": session_revenue,
        "booking_revenue": booking_revenue,
        "event_revenue": event_revenue,
        "total_revenue": sales_revenue + session_revenue + booking_revenue + event_revenue,
        "total_expenses": total_expenses,
        "profit_loss": sales_revenue + session_revenue + booking_revenue + event_revenue - total_expenses,
        "wallet_liability": wallet_liability,
        "payment_split": payment_split,
        "start": start,
        "end": end,
    }
    return render(request, "partner/accounting.html", context)


@role_required(PARTNER)
def export_report(request, report_type):
    mapping = {
        "sales": (Sale.objects.all(), ["created_at", "item_name", "category", "quantity", "amount", "payment_mode", "staff"]),
        "sessions": (GamingSession.objects.all(), ["start_time", "end_time", "station", "member", "amount", "payment_mode", "staff"]),
        "expenses": (Expense.objects.all(), ["date", "category", "amount", "description", "added_by", "reviewed"]),
        "wallet": (WalletLedger.objects.all(), ["created_at", "member", "transaction_type", "amount", "reason", "reference_type", "created_by"]),
        "bookings": (Booking.objects.all(), ["date", "start_time", "end_time", "customer", "booking_type", "amount", "payment_status", "booking_status"]),
        "event-registrations": (EventRegistration.objects.all(), ["created_at", "event", "customer", "payment_status", "registration_status"]),
    }
    if report_type not in mapping:
        messages.error(request, "Unknown report type.")
        return redirect("accounting_tracker")
    queryset, fields = mapping[report_type]
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{report_type}.csv"'
    writer = csv.writer(response)
    writer.writerow(fields)
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in fields])
    return response
