# Secure User Authentication System

A complete Django authentication and distributor management portal with Admin and Distributor roles, email OTP password reset, approval workflow, login lockout, audit logs, profile management and support tickets.

## Features

- Custom Django user model with Admin and Distributor roles
- Separate Admin and Distributor registration/login pages
- Distributor account approval workflow: Pending, Approved, Rejected, Blocked
- Admin distributor management: search, filter, view, approve, reject, block, delete
- Admin can manually create an approved distributor
- Email OTP password reset with 6-digit OTP and 5-minute expiry
- Development OTP display when using console email backend
- Failed login tracking and 10-minute lockout after 5 failed attempts
- Login activity logs with IP address and browser user agent
- Audit trail for important security and admin actions
- Profile page, edit profile, profile image upload and profile completion score
- Change password with email notification
- Distributor support ticket system with admin replies
- Bootstrap 5 responsive UI

## Run from zero

```bash
cd secure_auth_system
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create environment file:

```bash
copy .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Run database migrations:

```bash
python manage.py migrate
```

Create a Django superuser for `/admin/` if needed:

```bash
python manage.py createsuperuser
```

Start server:

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Important workflow

1. Register Admin from `/register/admin/`.
2. Register Distributor from `/register/distributor/`.
3. Distributor will be Pending and cannot login yet.
4. Admin logs in and opens Distributor Management.
5. Admin approves the distributor.
6. Distributor can now login and use dashboard/support tickets.

## OTP during development

Default `.env.example` uses Django console email backend. OTP is printed in terminal and also shown on OTP verification page while `DEBUG=True`.

## Real Gmail OTP email setup

Use a Gmail App Password, not your normal Gmail password.

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=yourgmail@gmail.com
EMAIL_HOST_PASSWORD=your_google_app_password
DEFAULT_FROM_EMAIL=Secure Auth <yourgmail@gmail.com>
```

## Main URLs

```text
/                         Home
/register/admin/          Admin registration
/login/admin/             Admin login
/register/distributor/    Distributor registration
/login/distributor/       Distributor login
/dashboard/admin/         Admin dashboard
/dashboard/distributor/   Distributor dashboard
/admin/distributors/      Distributor management
/admin/login-activity/    Login activity logs
/admin/audit-logs/        Audit logs
/support/                 Support tickets
/profile/                 Profile
```
