# Requirements Document

## Introduction

This document defines the requirements for the **Automobile Backend API**, a Django REST Framework (DRF) application that powers an automotive electronic repair and parts management platform. The system supports user authentication with chassis-level vehicle profiles, technical service and repair appointment tracking, a spare parts e-commerce catalog, a CMS for technical news and media, and administrative/diagnostic tooling. SQLite is used as the development database.

---

## Glossary

- **System**: The Automobile Backend API application as a whole.
- **Auth_Service**: The component responsible for user registration, login, logout, and password recovery.
- **User**: A registered customer with one or more vehicle profiles.
- **Admin**: A privileged user with elevated permissions to manage content, inventory, and appointments.
- **Chassis**: A Mercedes-Benz vehicle platform identifier (e.g., W204, W212) used to associate a user's vehicle. Valid values are drawn from the system's supported chassis list.
- **JWT**: JSON Web Token — a signed, time-limited token used for stateless authentication.
- **Appointment**: A repair request or diagnostic job submitted by a User for a specific vehicle module.
- **Service**: A technical capability offered by the workshop (e.g., ECU programming, EIS repair, FBS-4 sync).
- **Product**: A spare part in the inventory catalog, identified by OEM part number and chassis compatibility.
- **Article**: A technical news post, case study, or update published via the CMS.
- **Slug**: A URL-friendly string identifier derived from an Article's title.
- **Media_Item**: A gallery image representing a diagnostic procedure or completed repair.
- **Repair_Stage**: A named status in the repair workflow (e.g., "Pending", "In Diagnostics", "Syncing", "Ready", "Completed").
- **OEM_Number**: Original Equipment Manufacturer part number used to uniquely identify a spare part.
- **Token**: A secure, time-limited string used for password recovery.
- **Report**: A diagnostic PDF or binary scan file attached to an Appointment.

---

## Requirements

### Requirement 1: User Registration

**User Story:** As a new customer, I want to register an account with my vehicle chassis type, so that I can access repair services and parts tailored to my vehicle.

#### Acceptance Criteria

1. WHEN a POST request is made to `/api/auth/register` with a valid Name (1–150 characters), Email, Password meeting strength requirements, and a Chassis type from the system's supported list, THE Auth_Service SHALL create a new User account and return a 201 response with the created user's public profile (Name, Email, and registered Chassis types).
2. IF a POST request is made to `/api/auth/register` with an Email that already exists, THEN THE Auth_Service SHALL return a 400 response with a descriptive error message identifying the email conflict.
3. IF a POST request is made to `/api/auth/register` with a missing required field (Name, Email, Password, or Chassis type), THEN THE Auth_Service SHALL return a 400 response listing each missing field by name.
4. THE Auth_Service SHALL store passwords as cryptographic hashes (e.g., bcrypt or PBKDF2) and SHALL NOT store plaintext passwords.
5. IF a POST request is made to `/api/auth/register` with an invalid Email format, THEN THE Auth_Service SHALL return a 400 response with a field-level validation error on the `email` field.
6. IF a POST request is made to `/api/auth/register` with a Password that does not meet strength requirements (minimum 8 characters, at least one uppercase letter, one digit), THEN THE Auth_Service SHALL return a 400 response with a field-level validation error on the `password` field.

---

### Requirement 2: User Login

**User Story:** As a registered user, I want to log in with my credentials, so that I can receive a secure token to access protected endpoints.

#### Acceptance Criteria

1. WHEN a POST request is made to `/api/auth/login` with a valid Email and Password, THE Auth_Service SHALL return a 200 response containing an `access_token` (signed JWT) and a `refresh_token`.
2. IF a POST request is made to `/api/auth/login` with an incorrect Password or unregistered Email, THEN THE Auth_Service SHALL return a 401 response with a single generic error message that does not distinguish between the two failure cases.
3. IF a POST request is made to `/api/auth/login` with a missing Email or Password field, THEN THE Auth_Service SHALL return a 400 response identifying each missing field by name.
4. THE Auth_Service SHALL issue JWT access tokens with an expiry of no more than 60 minutes and refresh tokens with an expiry of no more than 7 days.
5. IF a POST request is made to `/api/auth/login` from a client that has exceeded 10 failed attempts within a 15-minute window, THEN THE Auth_Service SHALL return a 429 response with a `Retry-After` header indicating when the lockout expires.

---

### Requirement 3: User Logout

**User Story:** As a logged-in user, I want to log out, so that my session is invalidated and my account is protected.

#### Acceptance Criteria

1. WHEN a POST request is made to `/api/auth/logout` with a valid JWT in the Authorization header and the corresponding refresh token in the request body, THE Auth_Service SHALL mark the refresh token as invalidated and return a 200 response.
2. IF a POST request is made to `/api/auth/logout` with an absent or invalid JWT, THEN THE Auth_Service SHALL return a 401 response without modifying any session state.
3. IF a previously invalidated refresh token is submitted to any token-refresh endpoint, THEN THE Auth_Service SHALL return a 401 response.

---

### Requirement 4: Retrieve Current User Profile

**User Story:** As a logged-in user, I want to retrieve my account details and vehicle profiles, so that I can review my registered information.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/auth/me` with a valid JWT, THE Auth_Service SHALL return a 200 response containing the User's Name, Email, and list of registered Chassis types (which may be empty).
2. IF a GET request is made to `/api/auth/me` with an absent or invalid JWT, THEN THE Auth_Service SHALL return a 401 response.
3. IF a GET request is made to `/api/auth/me` with a valid JWT whose associated user record no longer exists, THEN THE Auth_Service SHALL return a 404 response.

---

### Requirement 5: Password Recovery

**User Story:** As a user who has forgotten their password, I want to receive a recovery email, so that I can securely reset my password.

#### Acceptance Criteria

1. WHEN a POST request is made to `/api/auth/forgot-password` with a registered Email, THE Auth_Service SHALL generate a secure, cryptographically random, time-limited Token.
2. WHEN a valid Token is generated per criterion 1, THE Auth_Service SHALL send a recovery email containing the Token to the registered Email address and return a 200 response.
3. IF a POST request is made to `/api/auth/forgot-password` with an unregistered Email, THEN THE Auth_Service SHALL return a 200 response without revealing whether the Email exists in the system.
4. THE Auth_Service SHALL generate password recovery Tokens that expire within 1 hour of issuance.
5. IF a password reset Token that has already been used or has expired is submitted, THEN THE Auth_Service SHALL return a 400 response with an error message indicating the Token is invalid or expired.
6. WHEN a valid, unexpired Token and a new Password meeting strength requirements are submitted to the password reset endpoint, THE Auth_Service SHALL update the User's password, invalidate the Token, and return a 200 response.

---

### Requirement 6: Service Directory

**User Story:** As a visitor or logged-in user, I want to browse the list of available technical services, so that I can understand what repairs and diagnostics are offered.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/services`, THE System SHALL return a 200 response containing a paginated list of all Services whose status is active (non-archived, enabled), with each entry including name, description, and supported Chassis types.
2. WHEN a GET request is made to `/api/services`, THE System SHALL return pagination metadata including `count` (total active services), `current_page`, `total_pages`, `next`, and `previous` fields, with a default page size of 20 items.
3. IF a GET request is made to `/api/services` with a `page` parameter that is out of range or non-numeric, THEN THE System SHALL return a 400 response with a descriptive error.

---

### Requirement 7: Service Detail

**User Story:** As a user, I want to view the full technical details of a specific service, so that I can determine if it is compatible with my vehicle.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/services/:id` with a valid integer Service ID, THE System SHALL return a 200 response with the Service's full details including name, description, compatible Chassis types, and estimated turnaround time in days.
2. IF a GET request is made to `/api/services/:id` with an ID that does not match any Service, THEN THE System SHALL return a 404 response.
3. IF a GET request is made to `/api/services/:id` with a malformed or non-integer ID, THEN THE System SHALL return a 400 response.

---

### Requirement 8: Book Appointment

**User Story:** As a logged-in user, I want to book a repair or diagnostic appointment for a specific module, so that I can schedule service for my vehicle.

#### Acceptance Criteria

1. WHEN a POST request is made to `/api/appointments/book` with a valid JWT, a valid Service ID, and a recognized Chassis type, THE System SHALL create a new Appointment with an initial Repair_Stage of "Pending" and return a 201 response containing the Appointment ID, Service ID, Chassis type, Repair_Stage, and creation timestamp.
2. IF a POST request is made to `/api/appointments/book` without a valid JWT, THEN THE System SHALL return a 401 response.
3. IF a POST request is made to `/api/appointments/book` with a Service ID that does not exist, THEN THE System SHALL return a 400 response with a descriptive error identifying the invalid Service ID.
4. IF a POST request is made to `/api/appointments/book` with a missing required field (Service ID or Chassis type), THEN THE System SHALL return a 400 response listing each missing field by name.
5. IF a POST request is made to `/api/appointments/book` with a Chassis type not in the system's supported chassis list, THEN THE System SHALL return a 400 response with a descriptive error identifying the unrecognized Chassis type.
6. IF a POST request is made to `/api/appointments/book` with a Chassis type that is not in the specified Service's compatible Chassis list, THEN THE System SHALL return a 400 response indicating the incompatibility.

---

### Requirement 9: User Appointment History

**User Story:** As a logged-in user, I want to view all my current and past repair appointments, so that I can track the status of my vehicles' service history.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/appointments/user` with a valid JWT, THE System SHALL return a 200 response containing a paginated list of all Appointments belonging to the authenticated User, ordered by creation date descending, with each entry including Appointment ID, Service name, Chassis type, current Repair_Stage, and creation date.
2. IF a GET request is made to `/api/appointments/user` without a valid JWT, THEN THE System SHALL return a 401 response.

---

### Requirement 10: Appointment Detail and Repair Timeline

**User Story:** As a logged-in user, I want to view the live repair timeline for a specific appointment, so that I can track the progress of my repair job.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/appointments/:id` with a valid JWT and an Appointment ID belonging to the authenticated User, THE System SHALL return a 200 response with the Appointment's full details including Appointment ID, Service name, Chassis type, creation date, current Repair_Stage, attached Report URL (if present), and a chronological list of all stage transitions each containing the Repair_Stage value and a UTC timestamp.
2. IF a GET request is made to `/api/appointments/:id` with a valid JWT and an Appointment ID that does not belong to the authenticated User, THEN THE System SHALL return a 403 response.
3. IF a GET request is made to `/api/appointments/:id` with a valid JWT and an Appointment ID that does not exist, THEN THE System SHALL return a 404 response.
4. IF a GET request is made to `/api/appointments/:id` without a valid JWT, THEN THE System SHALL return a 401 response.

---

### Requirement 11: Spare Parts Catalog

**User Story:** As a visitor or logged-in user, I want to browse the spare parts catalog with filters, so that I can find parts compatible with my vehicle.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/products`, THE System SHALL return a 200 response with a paginated list of Products (default page 1, default page size 20, maximum page size 100) including name, OEM_Number, price, stock level, and compatible Chassis types.
2. WHEN a GET request is made to `/api/products` with a `category` query parameter matching a known category, THE System SHALL return only Products belonging to that category.
3. WHEN a GET request is made to `/api/products` with a `chassis` query parameter matching a known Chassis type, THE System SHALL return only Products whose compatible Chassis list includes that Chassis type.
4. WHEN a GET request is made to `/api/products` with both `category` and `chassis` query parameters, THE System SHALL return only Products matching both filters simultaneously.
5. IF a GET request is made to `/api/products` with a `category` or `chassis` value that does not match any known value, THEN THE System SHALL return a 400 response with a descriptive error identifying the invalid filter value.

---

### Requirement 12: Spare Part Detail

**User Story:** As a user, I want to view the full details of a specific spare part, so that I can verify the OEM number and pricing before purchasing.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/products/:id` with a valid integer Product ID, THE System SHALL return a 200 response with the Product's full details including name, OEM_Number, description, price, stock level, and compatible Chassis types.
2. IF a GET request is made to `/api/products/:id` with an ID that does not match any Product, THEN THE System SHALL return a 404 response.
3. IF a GET request is made to `/api/products/:id` with a malformed or non-integer ID, THEN THE System SHALL return a 400 response.

---

### Requirement 13: Admin — Create Product

**User Story:** As an Admin, I want to add new spare parts to the catalog, so that customers can find and purchase them.

#### Acceptance Criteria

1. WHEN a POST request is made to `/api/admin/products` with a valid Admin JWT and all required fields (name ≤ 200 characters, OEM_Number, price ≥ 0.01, stock ≥ 0, compatible Chassis types array, category), THE System SHALL create a new Product and return a 201 response with the created Product's details.
2. IF a POST request is made to `/api/admin/products` with a valid JWT belonging to a non-Admin User, THEN THE System SHALL return a 403 response.
3. IF a POST request is made to `/api/admin/products` without a valid JWT, THEN THE System SHALL return a 401 response.
4. IF a POST request is made to `/api/admin/products` with a missing required field, THEN THE System SHALL return a 400 response listing each missing field by name.
5. IF a POST request is made to `/api/admin/products` with a duplicate OEM_Number, THEN THE System SHALL return a 400 response with an error message indicating the OEM_Number conflict.
6. IF a POST request is made to `/api/admin/products` with an invalid field value (price < 0.01, stock < 0, or name exceeding 200 characters), THEN THE System SHALL return a 400 response with a field-level validation error identifying the invalid field.

---

### Requirement 14: Admin — Update Product

**User Story:** As an Admin, I want to update a product's inventory, pricing, or compatibility, so that the catalog remains accurate.

#### Acceptance Criteria

1. WHEN a PATCH request is made to `/api/admin/products/:id` with a valid Admin JWT and one or more valid fields, THE System SHALL update only the provided fields of the Product and return a 200 response with the full updated Product.
2. IF a PATCH request is made to `/api/admin/products/:id` with a valid JWT belonging to a non-Admin User, THEN THE System SHALL return a 403 response.
3. IF a PATCH request is made to `/api/admin/products/:id` without a valid JWT, THEN THE System SHALL return a 401 response.
4. IF a PATCH request is made to `/api/admin/products/:id` with an ID that does not match any Product, THEN THE System SHALL return a 404 response.
5. IF a PATCH request is made to `/api/admin/products/:id` with an invalid field value (price < 0.01, stock < 0, or name exceeding 200 characters), THEN THE System SHALL return a 400 response with a field-level validation error identifying the invalid field, without modifying the Product.
6. IF a PATCH request is made to `/api/admin/products/:id` with an OEM_Number that already belongs to a different Product, THEN THE System SHALL return a 400 response with an error message indicating the OEM_Number conflict.

---

### Requirement 15: Technical News List

**User Story:** As a visitor or logged-in user, I want to browse technical articles and case studies, so that I can stay informed about automotive electronics.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/news`, THE System SHALL return a 200 response with a paginated list of published Articles (default page 1, default page size 20, maximum page size 100) including title, Slug, summary, author, and publication date, ordered by publication date descending.
2. IF a GET request is made to `/api/news`, THEN THE System SHALL only include Articles whose status is "published" in the response.
3. IF a GET request is made to `/api/news` and no published Articles exist, THEN THE System SHALL return a 200 response with an empty `results` array and `count` of 0.

---

### Requirement 16: Technical Article Detail

**User Story:** As a visitor or logged-in user, I want to read a full technical article by its slug, so that I can access detailed repair knowledge.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/news/:slug` where `:slug` is a non-empty URL-safe string matching a published Article's Slug, THE System SHALL return a 200 response with the Article's full content including title, body, author, publication date, and associated Media_Items.
2. IF a GET request is made to `/api/news/:slug` with a Slug that does not match any Article or matches an Article whose status is not "published", THEN THE System SHALL return a 404 response.

---

### Requirement 17: Media Gallery

**User Story:** As a visitor or logged-in user, I want to view the gallery of diagnostic procedures and completed repairs, so that I can assess the workshop's technical capability.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/media`, THE System SHALL return a 200 response with a paginated list of Media_Items whose visibility flag is "public" (default page 1, default page size 20, maximum page size 100), including image URL, caption, and upload date, ordered by upload date descending.
2. IF a GET request is made to `/api/media` and no public Media_Items exist, THEN THE System SHALL return a 200 response with an empty `results` array and `count` of 0.

---

### Requirement 18: Admin — Publish Article

**User Story:** As an Admin, I want to publish new technical articles, so that customers can access up-to-date repair knowledge.

#### Acceptance Criteria

1. WHEN a POST request is made to `/api/admin/news` with a valid Admin JWT and all required fields (title: 1–200 characters, body: 1–50,000 characters, author: 1–100 characters), THE System SHALL create a new Article, auto-generate a unique Slug from the title, and return a 201 response with the created Article including its ID, title, Slug, body, author, and publication date.
2. IF a POST request is made to `/api/admin/news` with a valid JWT belonging to a non-Admin User, THEN THE System SHALL return a 403 response.
3. IF a POST request is made to `/api/admin/news` without a valid JWT, THEN THE System SHALL return a 401 response.
4. IF a POST request is made to `/api/admin/news` with a title that would generate a duplicate Slug, THEN THE System SHALL append a numeric suffix starting at 1 and incrementing by 1 (up to a maximum of 999) to ensure Slug uniqueness.
5. IF a POST request is made to `/api/admin/news` with a missing or empty required field (title, body, or author), THEN THE System SHALL return a 400 response with a field-level error identifying each invalid field.

---

### Requirement 19: Admin — Media Upload

**User Story:** As an Admin, I want to upload high-resolution images to the media gallery, so that customers can view diagnostic and repair visuals.

#### Acceptance Criteria

1. WHEN a POST request is made to `/api/admin/media/upload` with a valid Admin JWT and a valid image file (JPEG, PNG, or WEBP, ≤ 10 MB), THE System SHALL store the image to the configured storage backend (local filesystem for development, S3/Cloudinary for production) and return a 201 response with the Media_Item's URL, filename, file size in bytes, MIME type, and upload timestamp.
2. IF a POST request is made to `/api/admin/media/upload` with a valid JWT belonging to a non-Admin User, THEN THE System SHALL return a 403 response.
3. IF a POST request is made to `/api/admin/media/upload` without a valid JWT, THEN THE System SHALL return a 401 response.
4. IF a POST request is made to `/api/admin/media/upload` with a file whose MIME type is not JPEG, PNG, or WEBP, THEN THE System SHALL return a 400 response with an error message indicating the accepted file types.
5. IF a POST request is made to `/api/admin/media/upload` with an image file exceeding 10 MB, THEN THE System SHALL return a 400 response indicating the file size limit.
6. IF a POST request is made to `/api/admin/media/upload` with no file attached, THEN THE System SHALL return a 400 response with a clear error indicating that a file is required.

---

### Requirement 20: Admin — List Users

**User Story:** As an Admin, I want to view all registered users and their chassis history, so that I can manage customer accounts and service eligibility.

#### Acceptance Criteria

1. WHEN a GET request is made to `/api/admin/users` with a valid Admin JWT, THE System SHALL return a 200 response with a paginated list of all Users (default page size 20, maximum 100) including their Name, Email, registration date, and associated Chassis types (which may be an empty array).
2. IF a GET request is made to `/api/admin/users` with a valid JWT belonging to a non-Admin User, THEN THE System SHALL return a 403 response.
3. IF a GET request is made to `/api/admin/users` without a valid JWT, THEN THE System SHALL return a 401 response.

---

### Requirement 21: Admin — Update Appointment Status

**User Story:** As an Admin, I want to advance a repair through its workflow stages, so that customers receive accurate real-time status updates.

#### Acceptance Criteria

1. WHEN a PATCH request is made to `/api/admin/appointments/:id/status` with a valid Admin JWT and a valid Repair_Stage value, THE System SHALL update the Appointment's Repair_Stage, record the stage transition with a server-generated UTC timestamp, and return a 200 response with the updated Appointment including the new Repair_Stage and full transition history.
2. IF a PATCH request is made to `/api/admin/appointments/:id/status` with a Repair_Stage value that is not one of the valid stage names ("Pending", "In Diagnostics", "Syncing", "Ready", "Completed"), THEN THE System SHALL return a 400 response listing all valid Repair_Stage values.
3. IF a PATCH request is made to `/api/admin/appointments/:id/status` with a valid JWT belonging to a non-Admin User, THEN THE System SHALL return a 403 response.
4. IF a PATCH request is made to `/api/admin/appointments/:id/status` with an Appointment ID that does not exist (after authentication is confirmed), THEN THE System SHALL return a 404 response.

---

### Requirement 22: Admin — Attach Diagnostic Report

**User Story:** As an Admin, I want to attach a diagnostic PDF or binary scan file to an appointment, so that the customer has a permanent record of their repair.

#### Acceptance Criteria

1. WHEN a POST request is made to `/api/admin/appointments/:id/report` with a valid Admin JWT and a valid file (PDF, application/octet-stream, or application/x-binary, ≤ 20 MB), THE System SHALL attach the Report to the specified Appointment and return a 200 response with the Report's storage URL, filename, file size in bytes, MIME type, and upload timestamp.
2. IF a POST request is made to `/api/admin/appointments/:id/report` with a valid JWT belonging to a non-Admin User, THEN THE System SHALL return a 403 response.
3. IF a POST request is made to `/api/admin/appointments/:id/report` with an Appointment ID that does not exist, THEN THE System SHALL return a 404 response.
4. IF a POST request is made to `/api/admin/appointments/:id/report` with a file whose MIME type is not PDF, application/octet-stream, or application/x-binary, THEN THE System SHALL return a 400 response with an error message listing the accepted file types.
5. IF a POST request is made to `/api/admin/appointments/:id/report` when the Appointment already has an attached Report, THEN THE System SHALL replace the existing Report with the new file and return a 200 response with the updated Report metadata.

---

### Requirement 23: API Pagination Consistency

**User Story:** As a developer consuming the API, I want all list endpoints to return consistent pagination metadata, so that I can build reliable client-side navigation.

#### Acceptance Criteria

1. THE System SHALL include `count` (total number of items across all pages), `next` (absolute URL of the next page or null), and `previous` (absolute URL of the previous page or null) fields in all paginated list responses.
2. THE System SHALL support a `page` query parameter on all list endpoints to navigate between pages, with page 1 as the default.
3. THE System SHALL support a `page_size` query parameter on all list endpoints, with a default of 20 and a maximum value of 100 items per page.
4. IF a `page` parameter is provided that exceeds the total number of pages, THEN THE System SHALL return a 404 response.

---

### Requirement 24: Global Error Response Format

**User Story:** As a developer consuming the API, I want all error responses to follow a consistent JSON structure, so that I can handle errors uniformly in client applications.

#### Acceptance Criteria

1. THE System SHALL return all error responses as JSON objects containing at minimum a `detail` field whose value is a non-empty string.
2. WHEN a validation error occurs, THE System SHALL return a JSON object where each key is the name of the invalid field and the value is a non-empty array of error message strings for that field.
