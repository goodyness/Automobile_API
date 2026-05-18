# Automobile Backend API — How-To Guide

This guide explains how to interact with every endpoint in the Automobile Backend API. All requests and responses use JSON unless the endpoint handles file uploads (multipart/form-data).

---

## Base URL

```
http://localhost:8000/api
```

---

## Authentication

Most endpoints require a JWT access token. Include it in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Access tokens expire after **60 minutes**. Use the refresh token to obtain a new one before expiry.

---

## 1. Auth & Security

### Register a New User

**POST** `/api/auth/register`

Creates a new user account. The `chassis` field must be one of the supported Mercedes-Benz platform codes.

**Supported chassis values:** `W204`, `W212`, `W205`, `W213`, `W176`, `W246`, `W166`, `W164`, `W221`, `W222`, `W251`, `W463`

**Request body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass1",
  "chassis": ["W204", "W212"]
}
```

**Password rules:** minimum 8 characters, at least one uppercase letter, at least one digit.

**Success — 201:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "chassis": ["W204", "W212"]
}
```

**Error — 400 (duplicate email):**
```json
{
  "email": ["A user with this email already exists."]
}
```

**Error — 400 (weak password):**
```json
{
  "password": ["Password must be at least 8 characters, contain one uppercase letter and one digit."]
}
```

---

### Login

**POST** `/api/auth/login`

Returns a JWT access token and a refresh token.

**Request body:**
```json
{
  "email": "john@example.com",
  "password": "SecurePass1"
}
```

**Success — 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Error — 401 (wrong credentials):**
```json
{
  "detail": "Invalid email or password."
}
```

**Error — 429 (rate limited after 10 failed attempts in 15 min):**
```json
{
  "detail": "Too many failed login attempts. Try again later.",
  "retry_after": 720
}
```
The `Retry-After` header is also set to the number of seconds until the lockout expires.

---

### Logout

**POST** `/api/auth/logout`

Invalidates the refresh token. Requires a valid JWT in the `Authorization` header.

**Request body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success — 200:**
```json
{
  "detail": "Successfully logged out."
}
```

---

### Get Current User Profile

**GET** `/api/auth/me`

Returns the authenticated user's profile and registered chassis types.

**Success — 200:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "chassis": ["W204", "W212"]
}
```

---

### Forgot Password

**POST** `/api/auth/forgot-password`

Sends a password recovery email. Always returns 200 regardless of whether the email is registered (to prevent user enumeration).

**Request body:**
```json
{
  "email": "john@example.com"
}
```

**Success — 200:**
```json
{
  "detail": "If this email is registered, a recovery link has been sent."
}
```

---

### Reset Password

**POST** `/api/auth/reset-password`

Resets the password using the token received by email. Tokens expire after 1 hour and can only be used once.

**Request body:**
```json
{
  "token": "abc123securetoken",
  "password": "NewSecurePass1"
}
```

**Success — 200:**
```json
{
  "detail": "Password has been reset successfully."
}
```

**Error — 400 (expired or used token):**
```json
{
  "detail": "This token is invalid or has expired."
}
```

---

## 2. Technical Services & Appointments

### List Services

**GET** `/api/services`

Returns a paginated list of all active services.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | 1 | Page number |
| `page_size` | integer | 20 | Items per page (max 100) |

**Success — 200:**
```json
{
  "count": 12,
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

### Service Detail

**GET** `/api/services/:id`

Returns full details for a single service.

**Success — 200:**
```json
{
  "id": 1,
  "name": "ECU Programming",
  "description": "Full ECU coding and adaptation for Mercedes-Benz platforms.",
  "compatible_chassis": ["W204", "W212", "W205"],
  "turnaround_days": 3
}
```

**Error — 404:** Service not found.
**Error — 400:** Non-integer ID supplied.

---

### Book an Appointment

**POST** `/api/appointments/book`

Requires authentication. Creates a new repair appointment with an initial stage of `"Pending"`.

**Request body:**
```json
{
  "service_id": 1,
  "chassis": "W204"
}
```

**Success — 201:**
```json
{
  "id": 42,
  "service_id": 1,
  "chassis": "W204",
  "stage": "Pending",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Error — 400 (chassis not compatible with service):**
```json
{
  "detail": "Chassis W176 is not compatible with service 'ECU Programming'."
}
```

**Error — 400 (unsupported chassis):**
```json
{
  "detail": "W999 is not a recognized chassis type."
}
```

---

### My Appointment History

**GET** `/api/appointments/user`

Requires authentication. Returns all appointments for the logged-in user, newest first.

**Success — 200:**
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

### Appointment Detail & Repair Timeline

**GET** `/api/appointments/:id`

Requires authentication. Returns full appointment details including the chronological stage transition history. Only the appointment owner can access this endpoint.

**Success — 200:**
```json
{
  "id": 42,
  "service_name": "ECU Programming",
  "chassis": "W204",
  "created_at": "2025-01-15T10:30:00Z",
  "stage": "Syncing",
  "report_url": null,
  "transitions": [
    { "stage": "Pending", "timestamp": "2025-01-15T10:30:00Z" },
    { "stage": "In Diagnostics", "timestamp": "2025-01-15T11:00:00Z" },
    { "stage": "Syncing", "timestamp": "2025-01-15T14:00:00Z" }
  ]
}
```

**Error — 403:** Appointment belongs to a different user.
**Error — 404:** Appointment not found.

---

## 3. Spare Parts Catalog

### List Products

**GET** `/api/products`

Returns a paginated list of spare parts. Supports optional filtering.

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `page` | integer | Page number (default 1) |
| `page_size` | integer | Items per page (default 20, max 100) |
| `category` | string | Filter by product category |
| `chassis` | string | Filter by compatible chassis (e.g. `W204`) |

**Success — 200:**
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

**Error — 400 (invalid filter value):**
```json
{
  "detail": "W999 is not a recognized chassis type."
}
```

---

### Product Detail

**GET** `/api/products/:id`

Returns full details for a single spare part.

**Success — 200:**
```json
{
  "id": 7,
  "name": "EIS Control Unit",
  "oem_number": "A2095450208",
  "description": "Original EIS unit for W204 and W212 platforms.",
  "price": "249.99",
  "stock": 5,
  "compatible_chassis": ["W204", "W212"]
}
```

---

## 4. Technical News & Media

### List News Articles

**GET** `/api/news`

Returns a paginated list of published articles, newest first.

**Success — 200:**
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
      "summary": "Step-by-step guide for FBS-4 synchronization on the S-Class W222.",
      "author": "Tech Team",
      "published_at": "2025-01-10T09:00:00Z"
    }
  ]
}
```

---

### Article Detail

**GET** `/api/news/:slug`

Returns the full content of a published article by its URL slug.

**Success — 200:**
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
      "caption": "FBS-4 connector location on W222"
    }
  ]
}
```

**Error — 404:** Slug not found or article is not published.

---

### Media Gallery

**GET** `/api/media`

Returns a paginated list of public gallery images, newest first.

**Success — 200:**
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

## 5. Admin Endpoints

All admin endpoints require a JWT belonging to a user with admin privileges (`is_staff = true`). Non-admin users receive a `403` response.

---

### Admin — Create Product

**POST** `/api/admin/products`

**Request body:**
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

**Success — 201:** Returns the created product object.

**Error — 400 (duplicate OEM number):**
```json
{
  "detail": "A product with OEM number A2095450208 already exists."
}
```

**Error — 400 (invalid price):**
```json
{
  "price": ["Price must be at least 0.01."]
}
```

---

### Admin — Update Product

**PATCH** `/api/admin/products/:id`

Send only the fields you want to update. Unspecified fields are left unchanged.

**Request body (example — update stock and price only):**
```json
{
  "stock": 15,
  "price": 229.99
}
```

**Success — 200:** Returns the full updated product object.

---

### Admin — Publish Article

**POST** `/api/admin/news`

**Request body:**
```json
{
  "title": "FBS-4 Sync Procedure for W222",
  "body": "Full article body text (up to 50,000 characters)...",
  "author": "Tech Team"
}
```

**Success — 201:**
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

If the generated slug already exists, a numeric suffix is appended automatically (e.g., `fbs-4-sync-procedure-for-w222-1`).

---

### Admin — Upload Media Image

**POST** `/api/admin/media/upload`

Use `multipart/form-data`. Accepted formats: JPEG, PNG, WEBP. Maximum file size: 10 MB.

**Form fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | Image file (JPEG, PNG, or WEBP) |
| `caption` | string | No | Optional caption for the image |
| `visibility` | string | No | `"public"` (default) or `"private"` |

**Success — 201:**
```json
{
  "url": "http://localhost:8000/media/gallery/ecu-repair-w204.jpg",
  "filename": "ecu-repair-w204.jpg",
  "file_size": 2048576,
  "mime_type": "image/jpeg",
  "uploaded_at": "2025-01-15T12:05:00Z"
}
```

**Error — 400 (wrong file type):**
```json
{
  "detail": "Unsupported file type. Accepted types: image/jpeg, image/png, image/webp."
}
```

**Error — 400 (file too large):**
```json
{
  "detail": "File size exceeds the 10 MB limit."
}
```

---

### Admin — List All Users

**GET** `/api/admin/users`

Returns a paginated list of all registered users.

**Success — 200:**
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

### Admin — Update Appointment Status

**PATCH** `/api/admin/appointments/:id/status`

Advances a repair through its workflow stages. Valid stages: `"Pending"`, `"In Diagnostics"`, `"Syncing"`, `"Ready"`, `"Completed"`.

**Request body:**
```json
{
  "stage": "In Diagnostics"
}
```

**Success — 200:**
```json
{
  "id": 42,
  "stage": "In Diagnostics",
  "transitions": [
    { "stage": "Pending", "timestamp": "2025-01-15T10:30:00Z" },
    { "stage": "In Diagnostics", "timestamp": "2025-01-15T11:00:00Z" }
  ]
}
```

**Error — 400 (invalid stage):**
```json
{
  "detail": "Invalid stage. Valid values are: Pending, In Diagnostics, Syncing, Ready, Completed."
}
```

---

### Admin — Attach Diagnostic Report

**POST** `/api/admin/appointments/:id/report`

Use `multipart/form-data`. Accepted formats: PDF, `application/octet-stream`, `application/x-binary`. Maximum file size: 20 MB.

If the appointment already has a report, it is replaced by the new file.

**Form fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | Report file (PDF or binary) |

**Success — 200:**
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

## 6. Pagination

All list endpoints support the same pagination parameters and return the same metadata structure.

**Query parameters:**

| Parameter | Default | Maximum | Description |
|---|---|---|---|
| `page` | 1 | — | Page number to retrieve |
| `page_size` | 20 | 100 | Number of items per page |

**Pagination response fields:**

| Field | Type | Description |
|---|---|---|
| `count` | integer | Total number of items across all pages |
| `current_page` | integer | The current page number |
| `total_pages` | integer | Total number of pages |
| `next` | string or null | Absolute URL of the next page, or null |
| `previous` | string or null | Absolute URL of the previous page, or null |
| `results` | array | Items on the current page |

If you request a page beyond `total_pages`, the API returns a `404` response.

---

## 7. Error Response Format

All error responses are JSON. There are two shapes:

**Generic error** (authentication, authorization, not found, etc.):
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

**Common HTTP status codes:**

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Resource created |
| 400 | Bad request / validation error |
| 401 | Authentication required or token invalid |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
