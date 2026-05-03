from __future__ import annotations

import asyncio
import io
import os
import threading
import zipfile
from dataclasses import dataclass
from typing import AsyncIterator, Literal
from xml.etree import ElementTree

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

from app.utils.config import settings
from app.utils.logger import get_logger
from app.utils.file_validation import UploadValidationError


logger = get_logger(__name__)

ImageMime = Literal["image/jpeg", "image/png"]


@dataclass(frozen=True)
class ImageBytes:
    data: bytes
    mime_type: ImageMime


def _render_text_to_images(text: str) -> list[ImageBytes]:
    # Render text into paginated images (no OCR involved).
    width, height = 1200, 1600
    margin = 40
    line_height = 18

    font = ImageFont.load_default()

    # Estimate characters per line for wrapping.
    # load_default() is monospace-ish, so this is a rough heuristic.
    max_chars_per_line = 90
    raw_lines: list[str] = []
    for paragraph in text.splitlines():
        # Preserve paragraph breaks with an empty line.
        if not paragraph.strip():
            raw_lines.append("")
            continue
        while len(paragraph) > max_chars_per_line:
            raw_lines.append(paragraph[:max_chars_per_line])
            paragraph = paragraph[max_chars_per_line:]
        raw_lines.append(paragraph)

    pages: list[list[str]] = []
    current: list[str] = []
    max_lines_per_page = (height - 2 * margin) // line_height
    for line in raw_lines:
        current.append(line)
        if len(current) >= max_lines_per_page:
            pages.append(current)
            current = []
    if current:
        pages.append(current)

    results: list[ImageBytes] = []
    for page_idx, page_lines in enumerate(pages):
        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)
        y = margin
        for line in page_lines:
            draw.text((margin, y), line, fill="black", font=font)
            y += line_height
        buf = io.BytesIO()
        # JPEG keeps payload smaller.
        img.save(buf, format="JPEG", quality=85, optimize=True)
        data = buf.getvalue()
        if len(data) > settings.max_image_bytes:
            raise UploadValidationError("Rendered text image exceeds safety limits.")
        results.append(ImageBytes(data=data, mime_type="image/jpeg"))
        if page_idx + 1 >= settings.max_pages:
            break
    return results


async def convert_file_to_images(*, filename: str, ext: str, detected_magic_type: str, file_bytes: bytes) -> AsyncIterator[ImageBytes]:
    """
    Converts supported input types into a stream of rendered page images.
    """
    if settings.max_upload_mb <= 0:
        raise UploadValidationError("Server misconfigured: max_upload_mb is invalid.")

    if len(file_bytes) == 0:
        raise UploadValidationError("Empty file.")

    if detected_magic_type == "pdf":
        async for img in _stream_pdf_to_images(file_bytes=file_bytes):
            yield img
        return

    if detected_magic_type == "docx":
        # Best-effort DOCX -> text/images without OCR.
        # For full fidelity conversion (tables/images), a DOCX->PDF tool is needed.
        text = _extract_docx_text(file_bytes)
        images = _render_text_to_images(text)
        for img in images[: settings.max_pages]:
            yield img
        return

    if detected_magic_type == "txt":
        try:
            text = file_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise UploadValidationError("Text decode failed for TXT upload.")
        images = _render_text_to_images(text)
        for img in images[: settings.max_pages]:
            yield img
        return

    if detected_magic_type in {"jpg", "png"}:
        # Validate image integrity and normalize to JPEG for Gemini.
        images = await _validate_and_normalize_image(
            file_bytes=file_bytes, detected_magic_type=detected_magic_type
        )
        for img in images:
            yield img
        return

    raise UploadValidationError("Unsupported detected content.")


async def _convert_pdf_to_images(*, file_bytes: bytes) -> list[ImageBytes]:
    def _work() -> list[ImageBytes]:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise UploadValidationError("Corrupted PDF upload.") from e
        results: list[ImageBytes] = []

        # Render higher quality for handwriting/smaller fonts.
        mat = fitz.Matrix(2.0, 2.0)  # scale x2
        for page_idx in range(min(doc.page_count, settings.max_pages)):
            page = doc.load_page(page_idx)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            # Convert to JPEG bytes.
            # PyMuPDF's `tobytes` signature differs across versions; use only the supported args.
            data = pix.tobytes("jpeg")
            if len(data) > settings.max_image_bytes:
                raise UploadValidationError("Rendered PDF page exceeds safety limits.")
            results.append(ImageBytes(data=data, mime_type="image/jpeg"))
        if doc.page_count > settings.max_pages:
            raise UploadValidationError("PDF has too many pages for processing limits.")
        return results

    return await asyncio.to_thread(_work)


async def _stream_pdf_to_images(*, file_bytes: bytes) -> AsyncIterator[ImageBytes]:
    """
    Streams PDF pages as images one-by-one.

    This keeps memory bounded and allows Gemini processing to start earlier.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[ImageBytes | UploadValidationError | None] = asyncio.Queue(maxsize=2)
    sentinel = None

    def worker():
        doc = None
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            if doc.page_count > settings.max_pages:
                raise UploadValidationError("PDF has too many pages for processing limits.")

            mat = fitz.Matrix(2.0, 2.0)  # scale x2
            for page_idx in range(doc.page_count):
                page = doc.load_page(page_idx)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                data = pix.tobytes("jpeg")
                if len(data) > settings.max_image_bytes:
                    raise UploadValidationError("Rendered PDF page exceeds safety limits.")

                img = ImageBytes(data=data, mime_type="image/jpeg")
                fut = asyncio.run_coroutine_threadsafe(queue.put(img), loop)
                fut.result()
        except UploadValidationError as e:
            # Forward known upload validation issues to the async consumer.
            fut = asyncio.run_coroutine_threadsafe(queue.put(e), loop)
            fut.result()
        except Exception:
            # Normalize unexpected conversion errors (corrupted/unreadable PDFs, etc).
            normalized = UploadValidationError("Corrupted PDF upload.")
            fut = asyncio.run_coroutine_threadsafe(queue.put(normalized), loop)
            fut.result()
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass
            fut = asyncio.run_coroutine_threadsafe(queue.put(sentinel), loop)
            fut.result()

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    while True:
        item = await queue.get()
        if item is sentinel:
            break
        if isinstance(item, UploadValidationError):
            raise item
        # Successful case: stream the rendered page image.
        if item is not None:
            yield item


async def _validate_and_normalize_image(*, file_bytes: bytes, detected_magic_type: str) -> list[ImageBytes]:
    def _work() -> list[ImageBytes]:
        try:
            img = Image.open(io.BytesIO(file_bytes))
            img.load()
        except Exception as e:
            raise UploadValidationError("Corrupted image upload.") from e

        # Normalize to RGB JPEG for Gemini input.
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        data = buf.getvalue()
        if len(data) > settings.max_image_bytes:
            raise UploadValidationError("Image exceeds safety limits.")
        return [ImageBytes(data=data, mime_type="image/jpeg")]

    return await asyncio.to_thread(_work)


def _extract_docx_text(docx_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
            # DOCX text is in word/document.xml
            with z.open("word/document.xml") as f:
                xml = f.read()
    except Exception as e:
        raise UploadValidationError("Corrupted DOCX upload.") from e

    # Minimal XML extraction: collect all <w:t> runs.
    try:
        root = ElementTree.fromstring(xml)
    except Exception as e:
        raise UploadValidationError("Failed to parse DOCX XML.") from e

    # Namespaced tags: {namespace}t
    texts: list[str] = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            texts.append(node.text)
    joined = "\n".join(texts).strip()
    if not joined:
        # Some DOCX may be image-only or contain no extractable text.
        return ""
    return joined

