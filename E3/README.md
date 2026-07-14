# E3 Lounge Management

A Django web app for E3 Lounge with role-based dashboards for partners, staff, and customers.

## Features

- Django authentication with Partner, Staff, and Customer groups
- Customer portal: registration, profile, member ID/QR, wallet, points, bookings, events
- Staff portal: tasks, daily checklists, member lookup, F&B sales, gaming sessions
- Partner portal: dashboard, members/staff operations, bookings, events, expenses, wallet ledger
- Accounting Tracker with revenue, expenses, profit/loss estimate, wallet liability, payment split, and CSV exports
- In-app notifications for welcome, booking, task, and event confirmations
- Render-ready settings for PostgreSQL, gunicorn, and WhiteNoise static files

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

## Demo Logins

Run `python manage.py seed_demo` first.

- Partner: `partner` / `partner123`
- Staff: `staff` / `staff123`
- Customer: `customer` / `customer123`

## Create a Superuser

```bash
python manage.py createsuperuser
```

To make a superuser behave as a partner in the app, add the user to the `Partner` group in Django admin.

## Environment Variables

- `SECRET_KEY`
- `DEBUG` (`False` in production)
- `DATABASE_URL` (Render PostgreSQL URL)
- `ALLOWED_HOSTS` (comma-separated hosts)
- `CSRF_TRUSTED_ORIGINS` (comma-separated HTTPS origins)
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `CASHFREE_APP_ID`
- `CASHFREE_SECRET_KEY`

SQLite is used automatically when `DATABASE_URL` is not set.

## Render Deployment

1. Create a new Render Web Service from this repository.
2. Add a Render PostgreSQL database.
3. Set `DATABASE_URL`, `SECRET_KEY`, `DEBUG=False`, and `ALLOWED_HOSTS`.
4. Use `./build.sh` as the build command.
5. Use `gunicorn e3_lounge.wsgi:application` as the start command, or let the `Procfile` handle it.
6. After deploy, run `python manage.py createsuperuser` from the Render shell.

## Production Uploads

The project includes Cloudinary dependencies and environment variable placeholders. For production file uploads, connect `django-cloudinary-storage` in settings before launch so receipts/media go to Cloudinary instead of local disk.

## Payment Notes

Phase 1 uses internal payment status tracking only. Real payments should be connected through hosted Razorpay or Cashfree checkout/payment links. Do not store card numbers or process raw card details in this app.
