# VerdantCare Homoeopathy Shop

A Django e-commerce foundation with homoeopathic medicines, doctor appointments, secure staff login, Django admin, dashboard metrics, SQLite database, and demo data.

## Windows quick start

1. Install Python 3.11+ from python.org and enable **Add Python to PATH**.
2. Double-click `setup.bat`.
3. Open `http://127.0.0.1:8000/dashboard/`.
4. Login with `admin` / `admin12345`.

Django admin is at `http://127.0.0.1:8000/admin/`. Change the demo password before using this beyond local development.

The generated database is `db.sqlite3`; `schema.sql` is included as a reference schema. The Django migration files are the source of truth for database creation.

## Reviews and notifications

- Customers can submit one rating/review per medicine from the medicines catalogue.
- Staff moderate reviews at `/manage/reviews/` or through Django admin.
- Order and appointment creates/status changes produce site and email notifications automatically.
- SMS delivery is recorded locally when a customer adds a phone number; connect a provider in `store/notifications.py` for production SMS.
- Run `python manage.py send_reminders` daily to notify customers whose appointment is tomorrow.

## Offers, website content, and security

- Staff manage coupons at `/manage/coupons/`, including percentage/fixed discounts, validity, minimum order, usage limit, and enable/disable.
- Staff manage banners, featured campaigns, About, Contact, FAQ, Privacy, Terms, and Shipping/Returns at `/manage/website/`.
- Payment is sandbox/token based locally; no card number is accepted or stored. Configure a hosted Stripe/Razorpay integration before production.
- Prescription files are validated to PDF/JPG/PNG up to 5 MB and stored outside public media, with owner/staff-only downloads.
- Password validation, PBKDF2 hashing, CSRF, HttpOnly/SameSite sessions, security headers, and RBAC groups are enabled.
- Run `python manage.py setup_roles` to create Content Manager, Order Manager, and Care Manager groups.
- Run `python manage.py backup_database` to create a timestamped JSON backup in `backups/`.

## Reports

- Staff reports are available at `/manage/reports/`.
- Sales: Daily, Weekly, Monthly, Yearly, with revenue/order totals and CSV export.
- Products: Best-selling products, low-stock medicines, and out-of-stock medicines.
- Customers: Registered customer count, active customer count, and recent registration list.
- Appointments: Total, doctor-wise, date-wise, completed, and cancelled summaries.
