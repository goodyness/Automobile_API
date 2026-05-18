# Automobile Backend API

A Django REST Framework backend for an automotive electronic repair and parts management platform. Built for a Mercedes-Benz–focused workshop offering ECU programming, EIS repair, FBS-4 synchronisation, and related electronic services.

---

## What it does

- **Customer registration** with OTP email verification
- **JWT authentication** (access + refresh tokens, token blacklisting on logout)
- **Repair appointment booking** with live stage tracking
- **Spare parts catalog** with chassis and category filtering
- **Technical news & media gallery** (CMS)
- **Admin tools** — manage users, advance repair stages, attach diagnostic reports
- **Admin accounts** created exclusively via `python manage.py createsuperuser` (no API endpoint)

---

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.10+ |
| Framework | Django 4.2 + Django REST Framework 3.15 |
| Auth | `djangorestframework-simplejwt` (JWT) |
| Database | SQLite (development) |
| Email | SMTP via Django email backend |
| Image handling | Pillow |
| Tests | pytest + pytest-django |

---

## Quick start

### 1. Clone and set up a virtual environment

```bash
git clone <repo-url>
cd automobile_backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure SMTP (for OTP and password recovery emails)

Open `config/settings/development.py` and fill in your SMTP credentials:

```python
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "your-email@gmail.com"
EMAIL_HOST_PASSWORD = "your-app-password"
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
```

> For local testing without real email, leave `EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"` (the default). OTPs will be stored in memory and visible in test output.

### 4. Apply migrations

```bash
python manage.py migrate
```

### 5. Create an admin account

```bash
python manage.py createsuperuser
```

Follow the prompts. This is the **only** way to create an admin — there is no `/api/auth/register` route for staff accounts.

### 6. Run the development server

```bash
python manage.py runserver
```

The API is now available at `http://localhost:8000/api/`.

---

## Running tests

```bash
python -m pytest tests/unit/
```

Run a specific test file:

```bash
python -m pytest tests/unit/test_auth.py -v
```

Run a specific test:

```bash
python -m pytest tests/unit/test_auth.py::TestVerifyOTP::test_valid_otp_creates_account_and_returns_tokens -v
```

> Tests use the in-memory email backend by default — no real SMTP connection is made.

---

## Project structure

```
automobile_backend/
├── manage.py
├── requirements.txt
├── pytest.ini
├── README.md
├── documentation.md
├── config/
│   ├── urls.py              ← root URL routing
│   ├── wsgi.py
│   └── settings/
│       ├── base.py          ← shared settings (JWT, DRF, SMTP declarations)
│       └── development.py   ← SQLite, locmem cache, locmem email
├── core/
│   ├── constants.py         ← chassis codes, repair stages
│   ├── exceptions.py        ← global error handler
│   ├── pagination.py        ← StandardPagination
│   ├── permissions.py       ← IsAdminUser
│   └── validators.py        ← password, chassis, image, report validators
├── apps/
│   ├── authentication/      ← register (OTP), verify-otp, login, logout, me, password recovery
│   ├── services/            ← service directory, appointment booking, repair timeline
│   ├── products/            ← spare parts catalog, admin CRUD
│   ├── cms/                 ← news articles, media gallery, admin publish/upload
│   └── admin_tools/         ← admin user list, appointment status, diagnostic reports
└── tests/
    └── unit/                ← 98 example-based tests
```

---

## API overview

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | Public | Step 1: validate data, send OTP |
| POST | `/api/auth/verify-otp` | Public | Step 2: verify OTP, create account |
| POST | `/api/auth/login` | Public | Get JWT tokens |
| POST | `/api/auth/logout` | User | Blacklist refresh token |
| GET | `/api/auth/me` | User | Get own profile |
| POST | `/api/auth/forgot-password` | Public | Send password reset email |
| POST | `/api/auth/reset-password` | Public | Reset password with token |
| GET | `/api/services` | Public | List active services |
| GET | `/api/services/:id` | Public | Service detail |
| POST | `/api/appointments/book` | User | Book a repair appointment |
| GET | `/api/appointments/user` | User | My appointment history |
| GET | `/api/appointments/:id` | User (owner) | Appointment detail + timeline |
| GET | `/api/products` | Public | Spare parts catalog |
| GET | `/api/products/:id` | Public | Part detail |
| GET | `/api/news` | Public | Published articles |
| GET | `/api/news/:slug` | Public | Article detail |
| GET | `/api/media` | Public | Public media gallery |
| POST | `/api/admin/products` | Admin | Create product |
| PATCH | `/api/admin/products/:id` | Admin | Update product |
| POST | `/api/admin/news` | Admin | Publish article |
| POST | `/api/admin/media/upload` | Admin | Upload gallery image |
| GET | `/api/admin/users` | Admin | List all users |
| PATCH | `/api/admin/appointments/:id/status` | Admin | Advance repair stage |
| POST | `/api/admin/appointments/:id/report` | Admin | Attach diagnostic report |

See `documentation.md` for full request/response examples.

---

## Environment variables (production)

For production, override these settings via environment variables or a `.env` file:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Set to `False` |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames |
| `EMAIL_HOST_USER` | SMTP username |
| `EMAIL_HOST_PASSWORD` | SMTP password / app password |
| `DEFAULT_FROM_EMAIL` | Sender address for outgoing emails |

---

## License

MIT
