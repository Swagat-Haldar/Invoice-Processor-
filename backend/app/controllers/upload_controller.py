from __future__ import annotations

import asyncio
from fastapi import UploadFile

from app.schemas.invoice import InvoiceExtraction
from app.services.file_processing import convert_file_to_images
from app.services.gemini_service import GeminiInvoiceExtractor
from app.utils.file_validation import UploadValidationError, validate_extension_and_magic
from app.utils.config import settings


async def _read_limited_upload(file: UploadFile, *, max_bytes: int) -> bytes:
    """
    Read file safely with a hard size limit.
    """
    size = 0
    chunks: list[bytes] = []
    while True:
        chunk = await file.read(1024 * 1024)  # 1MB chunks
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise UploadValidationError(f"File too large (>{max_bytes} bytes).")
        chunks.append(chunk)
    return b"".join(chunks)


async def handle_upload(*, file: UploadFile, gemini_extractor: GeminiInvoiceExtractor, max_upload_mb: int) -> InvoiceExtraction:
    if file is None:
        raise UploadValidationError("Missing file.")
    if not file.filename:
        raise UploadValidationError("Missing filename.")

    max_bytes = max_upload_mb * 1024 * 1024
    file_bytes = await _read_limited_upload(file, max_bytes=max_bytes)
    if not file_bytes:
        raise UploadValidationError("Empty file.")

    ext, detected_magic_type = validate_extension_and_magic(
        filename=file.filename, content_type=file.content_type, data=file_bytes
    )

    # Convert to page images and stream into Gemini.
    images_iter = convert_file_to_images(
        filename=file.filename,
        ext=ext,
        detected_magic_type=detected_magic_type,
        file_bytes=file_bytes,
    )

    # Hard timeout for "conversion + extraction" to prevent stuck requests.
    total_timeout_s = settings.conversion_timeout_s + settings.gemini_timeout_s
    invoice = await asyncio.wait_for(
        gemini_extractor.extract_from_images(images_iter),
        timeout=total_timeout_s,
    )
    return invoice

