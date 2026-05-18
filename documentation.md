# Automobile Backend API — Full Documentation

This document covers everything from installation to every API endpoint, including request/response examples, error formats, testing instructions, and SMTP configuration.

---

## Table of Contents

1. [Installation & Setup](#1-installation--setup)
2. [SMTP Configuration](#2-smtp-configuration)
3. [Running the Server](#3-running-the-server)
4. [Admin Account Setup](#4-admin-account-setup)
5. [Authentication](#5-authentication)
6. [Technical Services & Appointments](#6-technical-services--appointments)
7. [Spare Parts Catalog](#7-spare-parts-catalog)
8. [News & Media](#8-news--media)
9. [Admin Endpoints](#9-admin-endpoints)
10. [Pagination](#10-pagination)
11. [Error Responses](#11-error-responses)
12. [Running Tests](#12-running-tests)
13. [Supported Chassis Types](#13-supported-chassis-types)

---

## 1. Installation & Setup

### Requirements

- Python 3.10 or higher
- pip

### Step 1 — Clone the repository

```bash
git clone <repo-url>
cd automobile_backend
```

### Step 2 — Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

The `requirements.txt` includes:

| Package | Purpose |
|---|---|
| `Django==4.2.16` | Web framework |
| `djangorestframework==3.15.2` | REST API toolkit |
| `djangorestframework-simplejwt==5.3.1` | JWT authentication |
| `django-cors-headers==4.4.0` | CORS support |
| `Pillow` | Image processing for media uploads |
| `python-magic==0.4.27` | MIME type detection (optional, falls back to Content-Type) |
| `hypothesis==6.112.1` | Property-based testing |
| `pytest==8.3.3` | Test runner |
| `pytest-django==4.9.0` | Django integration for pytest |

### Step 4 — Apply database migrations

```bash
python manage.py migrate
```

This creates the SQLite database (`db.sqlite3`) with all tables.

---

## 2. SMTP Configuration

OTP verification emails and password recovery emails are sent via SMTP. Configure your credentials in `config/settings/development.py`:

```python
# Uncomment and fill in your SMTP details:
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"        # Gmail SMTP server
EMAIL_PORT = 587                     # TLS port
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "your-email@gmail.com"
EMAIL_HOST_PASSWORD = "your-app-password"  # Use an App Password for Gmail
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
```

### Gmail App Password setup

1. Go to your Google Account → Security → 2-Step Verification (must be enabled)
2. Under "App passwords", generate a new password for "Mail"
3. Use that 16-character password as `EMAIL_HOST_PASSWORD`

### Other providers

| Provider | EMAIL_HOST | EMAIL_PORT |
|---|---|---|
| Gmail | smtp.gmail.com | 587 |
| Outlook / Hotmail | smtp.office365.com | 587 |
| SendGrid | smtp.sendgrid.net | 587 |
| Mailgun | smtp.mailgun.org | 587 |

### Development without real email

Leave the default setting in `development.py` to use the in-memory backend — no emails are sent, OTPs are stored in memory and accessible in tests:

```python
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
```

---

## 3. Running the Server

```bash
python manage.py runserver
```

The API is available at: `http://localhost:8000/api/`

---

## 4. Admin Account Setup

Admin accounts **cannot** be created through the API. Use Django's management command:

```bash
python manage.py createsuperuser
```

You will be prompted for:
- Username (can be anything, email is used for login)
- Email address
- Password

Once created, log in using `POST /api/auth/login` with the email and password you set.

---

## 5. Authentication

All requests and responses use JSON. Protected endpoints require a JWT access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Access tokens expire after **60 minutes**. Use the refresh token to get a new one.

---

### 5.1 Register — Step 1: Send OTP

**POST** `/api/auth/register`

Validates your registration data and sends a 6-digit OTP to your email. The account is not created yet.

**Request:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass1",
  "chassis": ["W204", "W212"]
}
```

**Password rules:** minimum 8 characters, at least one uppercase letter, at least one digit.

**Chassis values:** must be from the supported list — see [Section 13](#13-supported-chassis-types).

**Response 200:**
```json
{
  "detail": "OTP sent to john@example.com. It expires in 10 minutes."
}
```

**Response 400 (validation error):**
```json
{
  "email": ["A user with this email already exists."],
  "password": ["Password must be at least 8 characters long."]
}
```

---

### 5.2 Register — Step 2: Verify OTP

**POST** `/api/auth/verify-otp`

Verifies the OTP and creates the account. Returns JWT tokens so you are immediately logged in.

**Request:**
```json
{
  "email": "john@example.com",
  "otp": "482910"
}
```

**Response 201:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "chassis": ["W204", "W212"],
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response 400 (wrong OTP):**
```json
{
  "detail": "Invalid OTP. Please check the code and try again."
}
```

**Response 400 (expired OTP):**
```json
{
  "detail": "OTP has expired. Please register again to receive a new code."
}
```

> OTPs expire after **10 minutes** and are single-use. If yours expires, call `/api/auth/register` again with the same data to get a fresh OTP.

---

### 5.3 Login

**POST** `/api/auth/login`

**Request:**
```json
{
  "email": "john@example.com",
  "password": "SecurePass1"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response 401 (wrong credentials):**
```json
{
  "detail": "Invalid email or password."
}
```

**Response 429 (rate limited — 10 failed attempts in 15 minutes):**
```json
{
  "detail": "Request was throttled.",
  "retry_after": 720
}
```
The `Retry-After` header is also set to the number of seconds until the lockout expires.

---

### 5.4 Refresh Access Token

**POST** `/api/auth/token/refresh`

**Request:**
```json
{
  "refresh": "<refresh_token>"
}
```

**Response 200:**
```json
{
  "access": "<new_access_token>"
}
```

---

### 5.5 Logout

**POST** `/api/auth/logout`  *(requires authentication)*

Blacklists the refresh token so it can no longer be used.

**Request:**
```json
{
  "refresh_token": "<refresh_token>"
}
```

**Response 200:**
```json
{
  "detail": "Successfully logged out."
}
```

---

### 5.6 Get Current User Profile

**GET** `/api/auth/me`  *(requires authentication)*

**Response 200:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "chassis": ["W204", "W212"]
}
```

---

### 5.7 Forgot Password

**POST** `/api/auth/forgot-password`

Always returns 200 regardless of whether the email is registered (prevents user enumeration).

**Request:**
```json
{
  "email": "john@example.com"
}
```

**Response 200:**
```json
{
  "detail": "If this email is registered, a recovery link has been sent."
}
```

---

### 5.8 Reset Password

**POST** `/api/auth/reset-password`

Use the token received in the recovery email. Tokens expire after **1 hour** and are single-use.

**Request:**
```json
{
  "token": "a3f9c2e1b4d8...",
  "password": "NewSecurePass1"
}
```

**Response 200:**
```json
{
  "detail": "Password has been reset successfully."
}
```

**Response 400 (expired or used token):**
```json
{
  "detail": "This token is invalid or has expired."
}
```

---

## 6. Technical Services & Appointments

### 6.1 List Services

**GET** `/api/services`

Returns all active workshop services. No authentication required.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | 1 | Page number |
| `page_size` | integer | 20 | Items per page (max 100) |

**Response 200:**
```json
{
  "count": 5,
  "current_page": 1,
  "total_pages": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "ECU Programming",
      "description": "Full ECU coding and adaptation for Mercedes-Benz platforms.",
      "compatible_chassis": ["W204", "W212", "W205"]
    }
  ]
}
```

---

### 6.2 Service Detail

**GET** `/api/services/:id`

**Response 200:**
```json
{
  "id": 1,
  "name": "ECU Programming",
  "description": "Full ECU coding and adaptation for Mercedes-Benz platforms.",
  "compatible_chassis": ["W204", "W212", "W205"],
  "turnaround_days": 3
}
```

**Response 404:** Service not found.  
**Response 400:** Non-integer ID supplied.

---

### 6.3 Book an Appointment

**POST** `/api/appointments/book`  *(requires authentication)*

**Request:**
```json
{
  "service_id": 1,
  "chassis": "W204"
}
```

**Response 201:**
```json
{
  "id": 42,
  "service_id": 1,
  "chassis": "W204",
  "stage": "Pending",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Response 400 (chassis not compatible with service):**
```json
{
  "chassis": ["Chassis W463 is not compatible with service 'ECU Programming'. Compatible chassis: W204, W212, W205."]
}
```

**Response 400 (unrecognized chassis):**
```json
{
  "chassis": ["'W999' is not a recognized chassis type."]
}
```

---

### 6.4 My Appointment History

**GET** `/api/appointments/user`  *(requires authentication)*

Returns all your appointments, newest first.

**Response 200:**
```json
{
  "count": 3,
  "current_page": 1,
  "total_pages": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 42,
      "service_name": "ECU Programming",
      "chassis": "W204",
      "stage": "In Diagnostics",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

---

### 6.5 Appointment Detail & Repair Timeline

**GET** `/api/appointments/:id`  *(requires authentication — owner only)*

**Response 200:**
```json
{
  "id": 42,
  "service_name": "ECU Programming",
  "chassis": "W204",
  "created_at": "2025-01-15T10:30:00Z",
  "stage": "Syncing",
  "report_url": null,
  "transitions": [
    { "stage": "Pending",        "timestamp": "2025-01-15T10:30:00Z" },
    { "stage": "In Diagnostics", "timestamp": "2025-01-15T11:00:00Z" },
    { "stage": "Syncing",        "timestamp": "2025-01-15T14:00:00Z" }
  ]
}
```

**Response 403:** Appointment belongs to a different user.  
**Response 404:** Appointment not found.

---

## 7. Spare Parts Catalog

### 7.1 List Products

**GET** `/api/products`

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `page` | integer | Page number (default 1) |
| `page_size` | integer | Items per page (default 20, max 100) |
| `category` | string | Filter by product category |
| `chassis` | string | Filter by compatible chassis (e.g. `W204`) |

**Response 200:**
```json
{
  "count": 45,
  "current_page": 1,
  "total_pages": 3,
  "next": "http://localhost:8000/api/products?page=2",
  "previous": null,
  "results": [
    {
      "id": 7,
      "name": "EIS Control Unit",
      "oem_number": "A2095450208",
      "price": "249.99",
      "stock": 5,
      "compatible_chassis": ["W204", "W212"]
    }
  ]
}
```

**Response 400 (invalid chassis filter):**
```json
{
  "chassis": ["'W999' is not a recognized chassis type."]
}
```

---

### 7.2 Product Detail

**GET** `/api/products/:id`

**Response 200:**
```json
{
  "id": 7,
  "name": "EIS Control Unit",
  "oem_number": "A2095450208",
  "description": "Original EIS unit for W204 and W212 platforms.",
  "price": "249.99",
  "stock": 5,
  "category": "Control Units",
  "compatible_chassis": ["W204", "W212"]
}
```

**Response 404:** Product not found.  
**Response 400:** Non-integer ID supplied.

---

## 8. News & Media

### 8.1 List News Articles

**GET** `/api/news`

Returns published articles only, newest first.

**Response 200:**
```json
{
  "count": 8,
  "current_page": 1,
  "total_pages": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "title": "FBS-4 Sync Procedure for W222",
      "slug": "fbs-4-sync-procedure-for-w222",
      "author": "Tech Team",
      "published_at": "2025-01-10T09:00:00Z"
    }
  ]
}
```

---

### 8.2 Article Detail

**GET** `/api/news/:slug`

**Response 200:**
```json
{
  "title": "FBS-4 Sync Procedure for W222",
  "slug": "fbs-4-sync-procedure-for-w222",
  "body": "Full article body text...",
  "author": "Tech Team",
  "published_at": "2025-01-10T09:00:00Z",
  "media_items": [
    {
      "url": "http://localhost:8000/media/gallery/fbs4-step1.jpg",
      "caption": "FBS-4 connector location on W222",
      "uploaded_at": "2025-01-09T08:00:00Z"
    }
  ]
}
```

**Response 404:** Slug not found or article is not published.

---

### 8.3 Media Gallery

**GET** `/api/media`

Returns public gallery images, newest first.

**Response 200:**
```json
{
  "count": 20,
  "current_page": 1,
  "total_pages": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "url": "http://localhost:8000/media/gallery/ecu-repair-w204.jpg",
      "caption": "ECU board repair on W204 platform",
      "uploaded_at": "2025-01-12T08:00:00Z"
    }
  ]
}
```

---

## 9. Admin Endpoints

All admin endpoints require a JWT belonging to a staff user (`is_staff = true`). Non-staff users receive `403`. Unauthenticated requests receive `401`.

Admin accounts are created with:
```bash
python manage.py createsuperuser
```

---

### 9.1 Create Product

**POST** `/api/admin/products`

**Request:**
```json
{
  "name": "EIS Control Unit",
  "oem_number": "A2095450208",
  "description": "Original EIS unit for W204 and W212 platforms.",
  "price": 249.99,
  "stock": 10,
  "category": "Control Units",
  "compatible_chassis": ["W204", "W212"]
}
```

**Response 201:** Returns the created product object.

**Response 400 (duplicate OEM number):**
```json
{
  "oem_number": ["A product with OEM number 'A2095450208' already exists."]
}
```

**Response 400 (invalid price):**
```json
{
  "price": ["Price must be at least 0.01."]
}
```

---

### 9.2 Update Product

**PATCH** `/api/admin/products/:id`

Send only the fields you want to update.

**Request (update stock and price only):**
```json
{
  "stock": 15,
  "price": 229.99
}
```

**Response 200:** Returns the full updated product object.

---

### 9.3 Publish Article

**POST** `/api/admin/news`

The slug is auto-generated from the title. If a collision occurs, a numeric suffix is appended (e.g. `my-title-1`).

**Request:**
```json
{
  "title": "FBS-4 Sync Procedure for W222",
  "body": "Full article body text (up to 50,000 characters)...",
  "author": "Tech Team"
}
```

**Response 201:**
```json
{
  "id": 5,
  "title": "FBS-4 Sync Procedure for W222",
  "slug": "fbs-4-sync-procedure-for-w222",
  "body": "Full article body text...",
  "author": "Tech Team",
  "published_at": "2025-01-15T12:00:00Z"
}
```

---

### 9.4 Upload Media Image

**POST** `/api/admin/media/upload`

Use `multipart/form-data`. Accepted formats: **JPEG, PNG, WEBP**. Maximum size: **10 MB**.

**Form fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | Image file |
| `caption` | string | No | Optional caption |
| `visibility` | string | No | `"public"` (default) or `"private"` |

**Response 201:**
```json
{
  "url": "http://localhost:8000/media/gallery/ecu-repair-w204.jpg",
  "filename": "ecu-repair-w204.jpg",
  "file_size": 2048576,
  "mime_type": "image/jpeg",
  "uploaded_at": "2025-01-15T12:05:00Z"
}
```

**Response 400 (wrong file type):**
```json
{
  "detail": "Unsupported file type 'text/plain'. Accepted types: image/jpeg, image/png, image/webp."
}
```

**Response 400 (file too large):**
```json
{
  "detail": "File size exceeds the 10 MB limit."
}
```

---

### 9.5 List All Users

**GET** `/api/admin/users`

**Response 200:**
```json
{
  "count": 150,
  "current_page": 1,
  "total_pages": 8,
  "next": "http://localhost:8000/api/admin/users?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com",
      "registered_at": "2025-01-01T08:00:00Z",
      "chassis": ["W204", "W212"]
    }
  ]
}
```

---

### 9.6 Update Appointment Status

**PATCH** `/api/admin/appointments/:id/status`

Valid stages (in order): `Pending` → `In Diagnostics` → `Syncing` → `Ready` → `Completed`

**Request:**
```json
{
  "stage": "In Diagnostics"
}
```

**Response 200:**
```json
{
  "id": 42,
  "stage": "In Diagnostics",
  "transitions": [
    { "stage": "Pending",        "timestamp": "2025-01-15T10:30:00Z" },
    { "stage": "In Diagnostics", "timestamp": "2025-01-15T11:00:00Z" }
  ]
}
```

**Response 400 (invalid stage):**
```json
{
  "stage": ["Invalid stage. Valid values are: Pending, In Diagnostics, Syncing, Ready, Completed."]
}
```

---

### 9.7 Attach Diagnostic Report

**POST** `/api/admin/appointments/:id/report`

Use `multipart/form-data`. Accepted formats: **PDF, application/octet-stream, application/x-binary**. Maximum size: **20 MB**.

If the appointment already has a report, it is replaced.

**Form fields:**

| Field | Type | Required |
|---|---|---|
| `file` | file | Yes |

**Response 200:**
```json
{
  "url": "http://localhost:8000/media/reports/appointment-42-scan.pdf",
  "filename": "appointment-42-scan.pdf",
  "file_size": 5242880,
  "mime_type": "application/pdf",
  "uploaded_at": "2025-01-15T15:00:00Z"
}
```

---

## 10. Pagination

All list endpoints return the same pagination envelope:

```json
{
  "count": 45,
  "current_page": 1,
  "total_pages": 3,
  "next": "http://localhost:8000/api/products?page=2",
  "previous": null,
  "results": [...]
}
```

| Field | Description |
|---|---|
| `count` | Total items across all pages |
| `current_page` | Current page number |
| `total_pages` | Total number of pages |
| `next` | URL of the next page, or `null` |
| `previous` | URL of the previous page, or `null` |
| `results` | Items on the current page |

**Query parameters available on all list endpoints:**

| Parameter | Default | Maximum |
|---|---|---|
| `page` | 1 | — |
| `page_size` | 20 | 100 |

Requesting a page beyond `total_pages` returns **404**.

---

## 11. Error Responses

All errors are JSON. Two shapes:

**Generic error** (auth, permissions, not found, etc.):
```json
{
  "detail": "A descriptive error message."
}
```

**Validation error** (invalid or missing fields):
```json
{
  "field_name": ["Error message for this field."],
  "another_field": ["First error.", "Second error."]
}
```

**HTTP status codes:**

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Resource created |
| 400 | Bad request / validation error |
| 401 | Authentication required or token invalid/expired |
| 403 | Insufficient permissions (not admin) |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## 12. Running Tests

### Run all unit tests

```bash
python -m pytest tests/unit/
```

### Run a specific test file

```bash
python -m pytest tests/unit/test_auth.py -v
python -m pytest tests/unit/test_services.py -v
python -m pytest tests/unit/test_products.py -v
python -m pytest tests/unit/test_cms.py -v
python -m pytest tests/unit/test_admin.py -v
```

### Run a single test

```bash
python -m pytest tests/unit/test_auth.py::TestVerifyOTP::test_valid_otp_creates_account_and_returns_tokens -v
```

### Run tests matching a keyword

```bash
python -m pytest tests/unit/ -k "login" -v
```

### What the tests cover

| File | Tests | Coverage |
|---|---|---|
| `test_auth.py` | 28 | Register (OTP flow), login, logout, me, password recovery |
| `test_services.py` | 19 | Service list/detail, booking, appointment history/detail |
| `test_products.py` | 19 | Catalog, filters, detail, admin create/update |
| `test_cms.py` | 18 | News list/detail, media gallery, admin publish/upload |
| `test_admin.py` | 14 | User list, appointment status, report attachment |

### Notes on email in tests

Tests use the in-memory email backend (`locmem`). No real emails are sent. OTPs are stored in the database and retrieved directly in tests — no inbox access needed.

---

## 13. Supported Chassis Types

The following Mercedes-Benz chassis codes are valid throughout the API (registration, appointment booking, product filtering):

| Code | Model |
|---|---|
| W204 | C-Class (2007–2014) |
| W212 | E-Class (2009–2016) |
| W205 | C-Class (2014–2021) |
| W213 | E-Class (2016–present) |
| W176 | A-Class (2012–2018) |
| W246 | B-Class (2011–2018) |
| W166 | ML/GLE-Class (2011–2019) |
| W164 | ML-Class (2005–2011) |
| W221 | S-Class (2005–2013) |
| W222 | S-Class (2013–2020) |
| W251 | R-Class (2005–2017) |
| W463 | G-Class (1989–present) |
