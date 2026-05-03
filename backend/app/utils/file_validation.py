from __future__ import annotations

import io
import zipfile

from typing import Literal


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".jpg", ".jpeg", ".png", ".txt"}

EXPECTED_MIME_BY_EXT: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".txt": "text/plain",
}


class UploadValidationError(Exception):
    pass


def _ext_normalize(filename: str) -> str:
    filename = filename or ""
    if "." not in filename:
        return ""
    return filename[filename.rfind(".") :].lower()


def detect_by_magic(data: bytes) -> str:
    """
    Returns one of: pdf, docx, jpg, png, txt.
    Raises UploadValidationError if unknown.
    """
    if data.startswith(b"%PDF"):
        return "pdf"
    # PNG magic
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    # JPEG magic
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    # DOCX is ZIP with specific entry names.
    if data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = set(z.namelist())
            if "[Content_Types].xml" in names and "word/document.xml" in names:
                return "docx"
            raise UploadValidationError("ZIP content is not a valid DOCX structure.")
        except UploadValidationError:
            raise
        except Exception as e:
            raise UploadValidationError("Corrupted DOCX upload.") from e
    # TXT: try utf-8 decode; if it succeeds reasonably, treat as txt.
    try:
        decoded = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as e:
        raise UploadValidationError("Unable to decode file as UTF-8 text.") from e
    if len(decoded.strip()) == 0:
        raise UploadValidationError("Text file is empty.")
    return "txt"


def validate_extension_and_magic(
    *, filename: str, content_type: str | None, data: bytes
) -> tuple[str, str]:
    """
    Validates both the provided extension and the content magic bytes.

    Returns (normalized_ext, detected_magic_type).
    """
    ext = _ext_normalize(filename)
    if not ext or ext not in ALLOWED_EXTENSIONS:
        raise UploadValidationError("Unsupported file type.")

    if not data:
        raise UploadValidationError("Empty file.")

    detected_magic_type = detect_by_magic(data)

    # Validate extension matches detected type.
    ext_to_magic = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".jpg": "jpg",
        ".jpeg": "jpg",
        ".png": "png",
        ".txt": "txt",
    }
    expected_magic_type = ext_to_magic.get(ext)
    if expected_magic_type != detected_magic_type:
        raise UploadValidationError("Fake extension or corrupted content.")

    # Validate MIME if provided (some clients may omit it; treat as optional).
    expected_mime = EXPECTED_MIME_BY_EXT.get(ext)
    if content_type:
        # Some browsers send octet-stream; treat as unacceptable when we can be strict.
        if content_type != expected_mime and content_type not in {f"application/octet-stream"}:
            # If it doesn't match expected, reject to satisfy "Validate MIME + extension".
            raise UploadValidationError("MIME type does not match file extension.")

    return ext, detected_magic_type

