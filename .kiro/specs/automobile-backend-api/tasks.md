# Implementation Plan: Automobile Backend API

## Overview

Incremental implementation of a Django REST Framework backend for an automotive electronic repair and parts management platform. Tasks are ordered so each phase builds on the previous one, ending with full integration. All 15 correctness properties from the design are covered by property-based tests using Hypothesis + pytest-django.

---

## Tasks

- [~] 1. Project setup — Django project, settings, dependencies, and SQLite
  - Create the `automobile_backend/` project layout with `config/settings/base.py`, `config/settings/development.py`, `config/settings/production.py`, `config/urls.py`, and `manage.py`
  - Install and pin all dependencies in `requirements.txt`: `django`, `djangorestframework`, `djangorestframework-simplejwt`, `django-cors-headers`, `python-magic`, `hypothesis`, `pytest`, `pytest-django`, `Pillow`
  - Configure `INSTALLED_APPS`, `DATABASES` (SQLite), `MEDIA_ROOT`, `MEDIA_URL`, `DEFAULT_AUTO_FIELD`, and `REST_FRAMEWORK` defaults in `base.py`
  - Add `SIMPLE_JWT` settings: `ACCESS_TOKEN_LIFETIME = timedelta(minutes=60)`, `REFRESH_TOKEN_LIFETIME = timedelta(days=7)`, `ROTATE_REFRESH_TOKENS = False`, `BLACKLIST_AFTER_ROTATION = True`
  - Create empty `apps/` package with sub-packages: `authentication`, `services`, `products`, `cms`, `admin_tools`
  - Create `core/` package with empty `pagination.py`, `exceptions.py`, `permissions.py`, `validators.py`
  - Add `pytest.ini` / `conftest.py` with `DJANGO_SETTINGS_MODULE = config.settings.development`
  - _Requirements: 23.1, 23.2, 23.3, 24.1_

- [x] 2. Core utilities — pagination, exception handler, permissions, validators
  - [x] 2.1 Implement `StandardPagination` in `core/pagination.py`
    - Subclass `PageNumberPagination`; set `page_size = 20`, `max_page_size = 100`, `page_size_query_param = "page_size"`
    - Override `get_paginated_response` to include `count`, `current_page`, `total_pages`, `next`, `previous`, `results`
    - Raise `NotFound` when requested page exceeds `total_pages`
    - _Requirements: 23.1, 23.2, 23.3, 23.4_

  - [x] 2.2 Implement global exception handler in `core/exceptions.py`
    - Write `custom_exception_handler(exc, context)` that normalises `AuthenticationFailed`, `NotAuthenticated`, `PermissionDenied`, `NotFound`, `ValidationError`, `Throttled`, and bare `Exception` to the two response shapes defined in the design
    - Include `retry_after` seconds in `Throttled` responses
    - Register handler in `REST_FRAMEWORK["EXCEPTION_HANDLER"]`
    - _Requirements: 24.1, 24.2_

  - [x] 2.3 Implement `IsAdminUser` permission in `core/permissions.py`
    - Check `request.user.is_authenticated and request.user.is_staff`
    - _Requirements: 13.2, 14.2, 18.2, 19.2, 20.2, 21.3, 22.2_

  - [x] 2.4 Implement validators in `core/validators.py`
    - `validate_password_strength(value)` — min 8 chars, ≥1 uppercase, ≥1 digit; raise `ValidationError` on failure
    - `validate_chassis(value)` — must be in `CHASSIS_CHOICES`; raise `ValidationError` on failure
    - `validate_image_file(file)` — MIME must be `image/jpeg`, `image/png`, or `image/webp`; size ≤ 10 MB; use `python-magic` for MIME detection
    - `validate_report_file(file)` — MIME must be `application/pdf`, `application/octet-stream`, or `application/x-binary`; size ≤ 20 MB
    - _Requirements: 1.6, 8.5, 19.4, 19.5, 22.4_

- [x] 3. Authentication app — User model, JWT, all auth endpoints
  - [x] 3.1 Create `User` and `UserChassis` models in `apps/authentication/models.py`
    - Extend `AbstractUser`; set `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = ["username"]`; add `name` CharField
    - Create `UserChassis` with FK to `User`, `chassis` CharField with `CHASSIS_CHOICES`, `unique_together = ("user", "chassis")`
    - Create `PasswordResetToken` model with `user` FK, `token` unique CharField(64), `created_at`, `used` BooleanField, and `is_expired()` method (1-hour window)
    - Set `AUTH_USER_MODEL = "authentication.User"` in settings
    - Run `makemigrations` and `migrate`
    - _Requirements: 1.1, 1.4, 5.4_

  - [x] 3.2 Implement `UserSerializer` and `RegisterView`
    - `UserSerializer` validates name, email uniqueness, password strength (via `validate_password_strength`), and chassis list (each via `validate_chassis`); hashes password with `set_password`
    - `RegisterView(CreateAPIView)` at `POST /api/auth/register`; permission `AllowAny`; returns 201 with name, email, chassis list
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 3.3 Implement `LoginSerializer`, `LoginView`, and login rate limiting
    - `LoginSerializer` validates email + password; returns token pair via `simplejwt`
    - `LoginRateLimitMixin` tracks failed attempts per IP in Django cache; threshold 10 / 15-minute window; raises `Throttled` with `Retry-After` on lockout
    - `LoginView(APIView)` at `POST /api/auth/login`; permission `AllowAny`; applies mixin
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.4 Implement `LogoutView`
    - `LogoutView(APIView)` at `POST /api/auth/logout`; permission `IsAuthenticated`
    - Blacklist the submitted refresh token using `simplejwt`'s `OutstandingToken` / `BlacklistedToken`
    - Return 200 `{"detail": "Successfully logged out."}`
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 3.5 Implement `MeView`
    - `MeView(RetrieveAPIView)` at `GET /api/auth/me`; permission `IsAuthenticated`
    - Return name, email, chassis list; return 404 if user record deleted mid-session
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 3.6 Implement `ForgotPasswordView` and `ResetPasswordView`
    - `ForgotPasswordView(APIView)` at `POST /api/auth/forgot-password`; always returns 200; generates `PasswordResetToken` and sends email when email is registered
    - `ResetPasswordView(APIView)` at `POST /api/auth/reset-password`; validates token not used and not expired; updates password; marks token used; returns 200
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ]* 3.7 Write property tests for authentication (Properties 1–5)
    - **Property 1: Password Strength Rejection** — `@given(st.text(max_size=7))` and strings without uppercase/digit; assert 400 and user count unchanged
    - **Validates: Requirements 1.6**
    - **Property 2: Duplicate Email Rejection** — register same email twice; assert second call returns 400 and user count stays at 1
    - **Validates: Requirements 1.2**
    - **Property 3: JWT Token Expiry Bounds** — after successful login, decode tokens and assert `exp - iat ≤ 3600` for access and `≤ 604800` for refresh
    - **Validates: Requirements 2.4**
    - **Property 4: Blacklisted Token Rejection** — logout with refresh token; attempt token-refresh; assert 401
    - **Validates: Requirements 3.3**
    - **Property 5: Password Recovery Token Expiry** — create token, manually set `created_at` to >1 hour ago, submit reset; assert 400
    - **Validates: Requirements 5.4, 5.5**
    - Place tests in `tests/property/test_auth_properties.py`

- [~] 4. Checkpoint — run all tests so far
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Services app — Service model, Appointment model, StageTransition, all views
  - [ ] 5.1 Create `Service`, `Appointment`, and `StageTransition` models
    - `Service`: name, description, turnaround_days, is_active, compatible_chassis (JSONField)
    - `Appointment`: FK to User and Service, chassis CharField, stage CharField (REPAIR_STAGES, default "Pending"), report fields (file, filename, file_size, mime_type, uploaded_at), created_at
    - `StageTransition`: FK to Appointment, stage, timestamp (auto_now_add); `Meta.ordering = ["timestamp"]`
    - Run `makemigrations` and `migrate`
    - _Requirements: 8.1, 10.1, 21.1_

  - [x] 5.2 Implement service directory views
    - `ServiceListView(ListAPIView)` at `GET /api/services`; permission `AllowAny`; filter `is_active=True`; use `StandardPagination`
    - `ServiceDetailView(RetrieveAPIView)` at `GET /api/services/:id`; return 404 for unknown ID, 400 for non-integer ID
    - _Requirements: 6.1, 6.2, 6.3, 7.1, 7.2, 7.3_

  - [x] 5.3 Implement appointment booking and user history views
    - `BookAppointmentView(CreateAPIView)` at `POST /api/appointments/book`; permission `IsAuthenticated`
    - Validate service exists, chassis in `CHASSIS_CHOICES`, chassis in `service.compatible_chassis`; create `Appointment` with stage "Pending"; create initial `StageTransition`
    - `UserAppointmentListView(ListAPIView)` at `GET /api/appointments/user`; permission `IsAuthenticated`; filter by `request.user`; order by `-created_at`; use `StandardPagination`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 9.1, 9.2_

  - [x] 5.4 Implement appointment detail view
    - `AppointmentDetailView(RetrieveAPIView)` at `GET /api/appointments/:id`; permission `IsAuthenticated`
    - Return 403 if `appointment.user != request.user`; return 404 if not found; include nested `StageTransitionSerializer` list
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [ ]* 5.5 Write property tests for appointments (Properties 6–7)
    - **Property 6: Appointment Ownership Isolation** — `@given` two distinct users; book appointment as user A; request detail as user B; assert 403 and no data leakage
    - **Validates: Requirements 10.2**
    - **Property 7: Chassis Compatibility Enforcement** — `@given` chassis value not in service's compatible list; attempt booking; assert 400 and no Appointment created
    - **Validates: Requirements 8.5, 8.6**
    - Place tests in `tests/property/test_appointment_properties.py`

- [x] 6. Products app — Product model, catalog views, admin CRUD
  - [x] 6.1 Create `Product` model in `apps/products/models.py`
    - Fields: name (max 200), oem_number (unique), description, price (DecimalField 10,2), stock (PositiveIntegerField), category, compatible_chassis (JSONField), created_at, updated_at
    - Run `makemigrations` and `migrate`
    - _Requirements: 11.1, 13.1_

  - [x] 6.2 Implement public product catalog views
    - `ProductListView(ListAPIView)` at `GET /api/products`; permission `AllowAny`; support `category` and `chassis` query params; validate chassis via `validate_chassis`; use `StandardPagination`
    - `ProductDetailView(RetrieveAPIView)` at `GET /api/products/:id`; return 404 / 400 as appropriate
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 12.1, 12.2, 12.3_

  - [x] 6.3 Implement admin product CRUD views
    - `AdminProductCreateView(CreateAPIView)` at `POST /api/admin/products`; permission `IsAdminUser`; validate price ≥ 0.01, stock ≥ 0, OEM uniqueness
    - `AdminProductUpdateView(UpdateAPIView)` at `PATCH /api/admin/products/:id`; permission `IsAdminUser`; partial update; validate same constraints
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

  - [ ]* 6.4 Write property tests for products (Properties 8–10)
    - **Property 8: Pagination Bounds Consistency** — `@given` valid page number P ≤ total_pages; assert `count` equals total qualifying records and `next` is null when P == total_pages
    - **Validates: Requirements 23.1, 23.3**
    - **Property 9: Product Filter Correctness** — `@given` chassis value C from CHASSIS_CHOICES; GET `/api/products?chassis=C`; assert every result has C in `compatible_chassis`
    - **Validates: Requirements 11.3**
    - **Property 10: OEM Number Uniqueness** — `@given` existing OEM number; attempt create or update with same OEM on different product; assert 400 and no DB change
    - **Validates: Requirements 13.5, 14.6**
    - Place tests in `tests/property/test_product_properties.py`

- [~] 7. Checkpoint — run all tests so far
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. CMS app — Article model, MediaItem model, news/media views, admin publish/upload
  - [x] 8.1 Create `Article` and `MediaItem` models in `apps/cms/models.py`
    - `Article`: title, slug (unique, auto-generated), body, author, status (draft/published), published_at, created_at
    - `MediaItem`: FK to Article (nullable), image (ImageField `upload_to="gallery/"`), caption, visibility (public/private), file_size, mime_type, uploaded_at
    - Implement `generate_unique_slug(title)` utility: slugify title, check DB, append numeric suffix 1–999 if collision
    - Run `makemigrations` and `migrate`
    - _Requirements: 15.1, 16.1, 17.1, 18.1, 18.4_

  - [x] 8.2 Implement public news and media views
    - `NewsListView(ListAPIView)` at `GET /api/news`; permission `AllowAny`; filter `status="published"`; order by `-published_at`; use `StandardPagination`
    - `NewsDetailView(RetrieveAPIView)` at `GET /api/news/:slug`; return 404 for unpublished or missing slug; include nested `MediaItemSerializer`
    - `MediaListView(ListAPIView)` at `GET /api/media`; permission `AllowAny`; filter `visibility="public"`; order by `-uploaded_at`; use `StandardPagination`
    - _Requirements: 15.1, 15.2, 15.3, 16.1, 16.2, 17.1, 17.2_

  - [x] 8.3 Implement admin article publish and media upload views
    - `AdminPublishArticleView(CreateAPIView)` at `POST /api/admin/news`; permission `IsAdminUser`; auto-generate slug via `generate_unique_slug`; set `status="published"` and `published_at=now()`
    - `AdminMediaUploadView(APIView)` at `POST /api/admin/media/upload`; permission `IsAdminUser`; validate file via `validate_image_file`; store to configured backend; return 201 with URL, filename, file_size, mime_type, uploaded_at
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 19.1, 19.2, 19.3, 19.4, 19.5, 19.6_

  - [ ]* 8.4 Write property tests for CMS (Properties 11, 13, 14)
    - **Property 11: Slug Uniqueness Under Collision** — `@given` article title that generates a duplicate slug; assert created article has a numeric-suffixed slug and is retrievable by that slug
    - **Validates: Requirements 18.4**
    - **Property 13: Published-Only Article Visibility** — `@given` mix of draft and published articles; GET `/api/news` and `/api/news/:slug`; assert no draft articles appear
    - **Validates: Requirements 15.2, 16.2**
    - **Property 14: File Type and Size Enforcement** — `@given` file with disallowed MIME type or size > 10 MB; POST to `/api/admin/media/upload`; assert 400 and no file persisted
    - **Validates: Requirements 19.4, 19.5**
    - Place tests in `tests/property/test_cms_properties.py`

- [ ] 9. Admin tools app — user list, appointment status update, report attachment
  - [x] 9.1 Implement `AdminUserListView`
    - `AdminUserListView(ListAPIView)` at `GET /api/admin/users`; permission `IsAdminUser`; return name, email, registered_at, chassis list; use `StandardPagination`
    - _Requirements: 20.1, 20.2, 20.3_

  - [x] 9.2 Implement `AdminAppointmentStatusView`
    - `AdminAppointmentStatusView(UpdateAPIView)` at `PATCH /api/admin/appointments/:id/status`; permission `IsAdminUser`
    - Validate stage is one of REPAIR_STAGES; update `appointment.stage`; create new `StageTransition` with server UTC timestamp; return updated appointment with full transition history
    - _Requirements: 21.1, 21.2, 21.3, 21.4_

  - [x] 9.3 Implement `AdminReportAttachView`
    - `AdminReportAttachView(APIView)` at `POST /api/admin/appointments/:id/report`; permission `IsAdminUser`
    - Validate file via `validate_report_file`; if appointment already has a report, delete old file from storage before saving new one; update report fields on Appointment; return 200 with URL, filename, file_size, mime_type, uploaded_at
    - _Requirements: 22.1, 22.2, 22.3, 22.4, 22.5_

  - [ ]* 9.4 Write property tests for admin tools (Properties 12, 15)
    - **Property 12: Stage Transition Append-Only History** — `@given` sequence of N valid stage updates; assert transitions list grows by exactly 1 per update, all prior entries unchanged, each has a UTC timestamp
    - **Validates: Requirements 21.1**
    - **Property 15: Report Replacement Idempotence** — attach report to appointment; attach a second report; assert appointment has exactly one report and it matches the second upload
    - **Validates: Requirements 22.5**
    - Place tests in `tests/property/test_cms_properties.py` (admin section) or `tests/property/test_admin_properties.py`

- [~] 10. Checkpoint — run all tests so far
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Unit tests — example-based coverage for all apps
  - [x] 11.1 Write unit tests for authentication endpoints
    - Cover: valid registration, duplicate email, weak password, missing fields, valid login, wrong credentials, missing fields, rate limit trigger, logout + blacklist, me endpoint, forgot-password (registered + unregistered), reset-password (valid, expired, used token)
    - Place in `tests/unit/test_auth.py`
    - _Requirements: 1.1–1.6, 2.1–2.5, 3.1–3.3, 4.1–4.3, 5.1–5.6_

  - [x] 11.2 Write unit tests for services and appointments
    - Cover: service list pagination, service detail (valid, 404, 400), book appointment (valid, 401, bad service, missing fields, bad chassis, incompatible chassis), user history, appointment detail (owner, non-owner 403, 404, 401)
    - Place in `tests/unit/test_services.py`
    - _Requirements: 6.1–6.3, 7.1–7.3, 8.1–8.6, 9.1–9.2, 10.1–10.4_

  - [x] 11.3 Write unit tests for products
    - Cover: list with/without filters, invalid filter value, detail (valid, 404, 400), admin create (valid, 403, 401, missing fields, duplicate OEM, invalid price/stock), admin update (valid, 403, 401, 404, invalid values, duplicate OEM)
    - Place in `tests/unit/test_products.py`
    - _Requirements: 11.1–11.5, 12.1–12.3, 13.1–13.6, 14.1–14.6_

  - [x] 11.4 Write unit tests for CMS
    - Cover: news list (published only, empty), article detail (valid slug, draft slug 404, missing slug 404), media gallery (public only, empty), admin publish (valid, 403, 401, missing fields, slug collision), admin upload (valid, 403, 401, wrong type, too large, no file)
    - Place in `tests/unit/test_cms.py`
    - _Requirements: 15.1–15.3, 16.1–16.2, 17.1–17.2, 18.1–18.5, 19.1–19.6_

  - [x] 11.5 Write unit tests for admin tools
    - Cover: user list (valid admin, 403, 401), appointment status update (valid, invalid stage, 403, 404), report attach (valid, 403, 404, wrong type, replacement)
    - Place in `tests/unit/test_admin.py`
    - _Requirements: 20.1–20.3, 21.1–21.4, 22.1–22.5_

- [x] 12. Wire everything together — URL routing and settings finalisation
  - [x] 12.1 Register all app URLs in `config/urls.py`
    - Mount `apps/authentication/urls.py` at `/api/auth/`
    - Mount `apps/services/urls.py` at `/api/`
    - Mount `apps/products/urls.py` at `/api/`
    - Mount `apps/cms/urls.py` at `/api/`
    - Mount `apps/admin_tools/urls.py` at `/api/admin/`
    - Add `simplejwt` token-refresh endpoint at `/api/auth/token/refresh/`
    - Serve `MEDIA_URL` via `static()` in development
    - _Requirements: all endpoint requirements_

  - [x] 12.2 Finalise `development.py` settings
    - Set `DEBUG = True`, `ALLOWED_HOSTS = ["localhost", "127.0.0.1"]`
    - Configure `CACHES` with `LocMemCache` for rate limiting
    - Configure `EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"`
    - Configure `DEFAULT_FILE_STORAGE` for local filesystem
    - _Requirements: 2.5, 5.2_

  - [ ]* 12.3 Write integration / end-to-end tests
    - Full user journey: register → login → book appointment → view timeline → logout
    - Admin journey: login as admin → create product → publish article → upload media → update appointment status → attach report
    - Verify pagination metadata on all list endpoints
    - Verify error format on all error paths
    - Place in `tests/integration/` or extend `tests/unit/` with `@pytest.mark.django_db` integration markers
    - _Requirements: 23.1–23.4, 24.1–24.2_

- [x] 13. Final checkpoint — full test suite
  - Ensure all tests pass, ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property-based tests use `@settings(max_examples=100)` and are tagged with `# Feature: automobile-backend-api, Property N: <text>`
- Unit tests and property tests are complementary — both must pass before moving to the next phase
- Checkpoints at tasks 4, 7, 10, and 13 ensure incremental validation
- `python-magic` is used for server-side MIME detection (magic bytes, not `Content-Type` header)
- Report replacement (Property 15) must delete the old file from storage to avoid orphaned files

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["2.1", "2.2", "2.3", "2.4"] },
    { "id": 1, "tasks": ["3.1"] },
    { "id": 2, "tasks": ["3.2", "3.3", "3.4", "3.5", "3.6"] },
    { "id": 3, "tasks": ["3.7", "5.1"] },
    { "id": 4, "tasks": ["5.2", "5.3", "5.4", "6.1", "8.1"] },
    { "id": 5, "tasks": ["5.5", "6.2", "6.3", "8.2", "8.3", "9.1"] },
    { "id": 6, "tasks": ["6.4", "8.4", "9.2", "9.3"] },
    { "id": 7, "tasks": ["9.4", "11.1", "11.2", "11.3", "11.4", "11.5"] },
    { "id": 8, "tasks": ["12.1", "12.2"] },
    { "id": 9, "tasks": ["12.3"] }
  ]
}
```
