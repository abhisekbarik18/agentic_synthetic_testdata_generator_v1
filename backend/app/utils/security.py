"""
Security utilities — SQL sanitisation, file-size guards, synthetic-data safeguards.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.config import settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# ── SQL export safety ────────────────────────────────────────────────────────

# Statements that must never appear in generated SQL INSERT scripts.
_DANGEROUS_SQL = re.compile(
    r"\b(DROP|ALTER|TRUNCATE|DELETE|UPDATE|GRANT|REVOKE|EXEC|EXECUTE|CREATE\s+USER|"
    r"xp_cmdshell|UNION\s+SELECT|--|;.*;)\b",
    re.IGNORECASE,
)


def sanitise_sql_value(value: str) -> str:
    """Escape single quotes for safe SQL INSERT values."""
    return value.replace("'", "''")


def validate_sql_safety(sql: str) -> bool:
    """Return True if the SQL string contains only safe INSERT statements."""
    if _DANGEROUS_SQL.search(sql):
        logger.warning("Blocked potentially dangerous SQL content.")
        return False
    return True


# ── File-size guard ──────────────────────────────────────────────────────────

def check_export_file_size(path: Path) -> bool:
    """Return True if the file is within the configured size limit."""
    max_bytes = settings.MAX_EXPORT_FILE_SIZE_MB * 1024 * 1024
    if path.exists() and path.stat().st_size > max_bytes:
        logger.warning(
            "Export file %s exceeds limit (%s MB).", path, settings.MAX_EXPORT_FILE_SIZE_MB
        )
        return False
    return True


# ── Synthetic-data safeguards ────────────────────────────────────────────────

# Patterns that look like real PII and should trigger a warning.
_REAL_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_REAL_CC = re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b")


def flag_potential_pii(text: str) -> list[str]:
    """Return a list of warnings if the text contains patterns that resemble real PII."""
    warnings: list[str] = []
    if _REAL_SSN.search(text):
        warnings.append("Data contains values resembling real SSNs — verify they are synthetic.")
    if _REAL_CC.search(text):
        warnings.append("Data contains values resembling real credit-card numbers — verify they are synthetic.")
    return warnings


# ── Path traversal guard ────────────────────────────────────────────────────

def safe_filename(name: str) -> str:
    """Strip path-traversal characters from a user-supplied filename."""
    # Remove path traversal sequences (../, ..\, etc.)
    cleaned = re.sub(r"(\.\.[\\/]*)+", "", name)
    # Keep only alphanumerics, hyphens, underscores, and dots.
    cleaned = re.sub(r"[^\w.\-]", "_", cleaned)
    # Remove leading dots and underscores to prevent hidden files / traversal.
    return cleaned.lstrip("._")

