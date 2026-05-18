"""
Shared constants for the Automobile Backend API.
"""

# Supported Mercedes-Benz chassis platform identifiers.
# Used for validation across authentication, services, products, and appointments.
CHASSIS_CHOICES = [
    ("W204", "W204 — C-Class (2007–2014)"),
    ("W212", "W212 — E-Class (2009–2016)"),
    ("W205", "W205 — C-Class (2014–2021)"),
    ("W213", "W213 — E-Class (2016–present)"),
    ("W176", "W176 — A-Class (2012–2018)"),
    ("W246", "W246 — B-Class (2011–2018)"),
    ("W166", "W166 — ML/GLE-Class (2011–2019)"),
    ("W164", "W164 — ML-Class (2005–2011)"),
    ("W221", "W221 — S-Class (2005–2013)"),
    ("W222", "W222 — S-Class (2013–2020)"),
    ("W251", "W251 — R-Class (2005–2017)"),
    ("W463", "W463 — G-Class (1989–present)"),
]

# Flat list of valid chassis codes for quick membership checks.
VALID_CHASSIS_CODES = [code for code, _ in CHASSIS_CHOICES]

# Repair workflow stages (ordered).
REPAIR_STAGES = [
    ("Pending", "Pending"),
    ("In Diagnostics", "In Diagnostics"),
    ("Syncing", "Syncing"),
    ("Ready", "Ready"),
    ("Completed", "Completed"),
]

VALID_REPAIR_STAGES = [stage for stage, _ in REPAIR_STAGES]

# File upload limits
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024   # 10 MB
MAX_REPORT_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_REPORT_MIME_TYPES = {"application/pdf", "application/octet-stream", "application/x-binary"}
