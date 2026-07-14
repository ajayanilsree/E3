import re

from django import forms
from django.contrib.auth.models import Group, User
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import (
    Booking,
    ChecklistTemplate,
    DailyChecklist,
    Event,
    EventRegistration,
    Expense,
    GamingSession,
    MemberProfile,
    PointTransaction,
    Sale,
    Task,
    WalletLedger,
)
from .roles import CUSTOMER, STAFF


def normalize_phone(value):
    return re.sub(r"\D", "", value or "")


class CustomerRegistrationForm(forms.Form):
    full_name = forms.CharField(
        max_length=160,
        widget=forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Full Name"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "Email Address"}),
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "username", "placeholder": "Username"}),
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Password"}),
    )
    password2 = forms.CharField(
        label="Repeat Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Repeat Password"}),
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "placeholder": "Date of Birth"}),
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel", "placeholder": "Mobile Number"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already exists with this email.")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if len(phone) < 10:
            raise forms.ValidationError("Enter a valid phone number.")
        if MemberProfile.objects.filter(phone=phone).exists():
            raise forms.ValidationError("An account already exists with this phone number. Please log in.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned_data

    def save(self):
        full_name = self.cleaned_data["full_name"].strip()
        parts = full_name.split(" ", 1)
        phone = self.cleaned_data["phone"]
        user = User(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else "",
        )
        user.set_password(self.cleaned_data["password1"])
        user.save()
        group, _ = Group.objects.get_or_create(name=CUSTOMER)
        user.groups.add(group)
        profile = user.member_profile
        profile.phone = phone
        profile.save()
        return user


class PartnerAdminAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.groups.filter(name=CUSTOMER).exists() and not user.is_staff and not user.is_superuser:
            raise forms.ValidationError("Customers must log in with phone number and OTP.", code="customer_otp_required")


class CustomerPasswordLoginForm(forms.Form):
    username = forms.CharField(
        label="Username / Email",
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "username", "placeholder": "Enter your username"}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "placeholder": "Enter your password"}),
    )


class CustomerOTPVerificationForm(forms.Form):
    otp = forms.CharField(
        label="OTP",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code", "class": "otp-input"}),
    )

    def clean_otp(self):
        otp = self.cleaned_data["otp"].strip()
        if not otp.isdigit():
            raise forms.ValidationError("Enter the 6-digit OTP.")
        return otp


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["booking_type", "date", "start_time", "end_time", "amount"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }


class BookingStatusForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["payment_status", "booking_status"]


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["name", "description", "date", "time", "entry_fee", "capacity", "status"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}), "time": forms.TimeInput(attrs={"type": "time"})}


class EventRegistrationStatusForm(forms.ModelForm):
    class Meta:
        model = EventRegistration
        fields = ["payment_status", "registration_status"]


class MemberLookupForm(forms.Form):
    query = forms.CharField(label="Member ID, phone, email, or username", max_length=120)


class WalletLedgerForm(forms.ModelForm):
    class Meta:
        model = WalletLedger
        fields = ["member", "transaction_type", "amount", "reason", "reference_type"]


class PointTransactionForm(forms.ModelForm):
    class Meta:
        model = PointTransaction
        fields = ["member", "points", "reason"]


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ["member", "category", "item_name", "quantity", "amount", "payment_mode"]


class GamingSessionForm(forms.ModelForm):
    class Meta:
        model = GamingSession
        fields = ["member", "station", "start_time", "end_time", "amount", "payment_mode"]
        widgets = {
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["category", "amount", "description", "receipt", "date"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class TaskForm(forms.ModelForm):
    assigned_to = forms.ModelChoiceField(queryset=User.objects.none())

    class Meta:
        model = Task
        fields = ["title", "description", "assigned_to", "priority", "status", "due_date"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(groups__name=STAFF).order_by("first_name", "username")


class TaskStatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["status"]


class ChecklistTemplateForm(forms.ModelForm):
    class Meta:
        model = ChecklistTemplate
        fields = ["name", "checklist_type", "items"]


class DailyChecklistForm(forms.ModelForm):
    assigned_to = forms.ModelChoiceField(queryset=User.objects.none())

    class Meta:
        model = DailyChecklist
        fields = ["date", "template", "assigned_to", "status"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(groups__name=STAFF).order_by("first_name", "username")


class StaffUserForm(UserCreationForm):
    first_name = forms.CharField(max_length=80)
    last_name = forms.CharField(max_length=80, required=False)
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.is_staff = True
        if commit:
            user.save()
            group, _ = Group.objects.get_or_create(name=STAFF)
            user.groups.add(group)
        return user
