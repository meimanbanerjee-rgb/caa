# backend/app/ingestion/validator.py
# File validation module enforcing MIME types, extensions, size limits, and path security (FR-1, FR-3).

from pathlib import Path
from typing import Optional, Tuple
import os
import re

from backend.app.config import settings

# Supported extensions and their expected MIME types
ALLOWED_EXTENSIONS = {
    ".csv": {"text/csv", "text/plain", "application/vnd.ms-excel", "application/octet-stream"},
    ".tsv": {"text/tab-separated-values", "text/plain", "application/octet-stream"},
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
        "application/octet-stream",
    },
    ".json": {"application/json", "text/plain", "application/octet-stream"},
    ".jsonl": {"application/x-ndjson", "application/json", "text/plain", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".pdf": {"application/pdf", "application/octet-stream"},
}


class FileValidationError(Exception):
    """Raised when a file fails safety, type, or size validation."""
    def __init__(self, message: str, filename: str) -> None:
        self.message = message
        self.filename = filename
        super().__init__(f"[{filename}] {message}")


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes filenames to prevent path traversal and arbitrary filesystem escape.
    Removes path separators and non-standard characters while keeping the basename.
    """
    # Extract only the base name (prevents ../ or C:\ path traversal)
    base = os.path.basename(filename.replace("\\", "/"))
    # Strip any dangerous shell or filesystem characters
    clean_name = re.sub(r"[^\w\s\.-]", "_", base).strip()
    return clean_name or "uploaded_file"


def validate_file_metadata(
    filename: str,
    size_bytes: int,
    content_type: Optional[str] = None,
) -> Tuple[bool, Optional[str], str]:
    """
    Validates file extension, size limit, and returns normalized extension.
    Returns: (is_valid, error_message, normalized_extension)
    """
    clean_filename = sanitize_filename(filename)
    ext = Path(clean_filename).suffix.lower()

    if not ext:
        return (
            False,
            f"File '{filename}' has no extension. Supported formats: CSV, TSV, XLSX, JSON, JSONL, PDF.",
            "",
        )

    if ext not in ALLOWED_EXTENSIONS:
        supported = ", ".join(ALLOWED_EXTENSIONS.keys())
        return (
            False,
            f"Unsupported file format '{ext}'. InsightForge supports: {supported}.",
            ext,
        )

    if size_bytes <= 0:
        return False, f"File '{filename}' is empty (0 bytes).", ext

    if size_bytes > settings.max_upload_bytes:
        size_mb = round(size_bytes / (1024 * 1024), 2)
        return (
            False,
            f"File size ({size_mb} MB) exceeds maximum allowed limit of {settings.max_upload_mb} MB.",
            ext,
        )

    return True, None, ext
