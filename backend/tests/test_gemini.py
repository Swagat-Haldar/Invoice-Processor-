from __future__ import annotations

import asyncio
from typing import AsyncIterator

import pytest

from app.schemas.invoice import InvoiceExtraction
from app.services.gemini_service import GeminiInvoiceExtractor
from app.services import gemini_service
from app.utils.file_validation import UploadValidationError
from app.services.file_processing import ImageBytes


def make_images(jpeg_bytes: bytes) -> AsyncIterator[ImageBytes]:
    async def _iter():
        yield ImageBytes(data=jpeg_bytes, mime_type="image/jpeg")

    return _iter()


@pytest.mark.asyncio
async def test_gemini_timeout_retry_works(monkeypatch: pytest.MonkeyPatch):
    from .conftest import make_jpeg_bytes

    call_count = {"n": 0}

    class FakeResponse:
        def __init__(self, text: str):
            self.text = text

    class FakeModel:
        def generate_content(self, parts):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise TimeoutError("Simulated timeout")
            return FakeResponse(
                text=(
                    '{"invoice_meta":{"original_language":"en"},"seller":{},"buyer":{},'
                    '"line_items":[],"totals":{},"payment":{},"notes":"","other":{}}'
                )
            )

    monkeypatch.setattr(gemini_service.genai, "GenerativeModel", lambda _: FakeModel())

    extractor = GeminiInvoiceExtractor(api_key="dummy", model_name="fake")
    images = make_images(make_jpeg_bytes())
    result: InvoiceExtraction = await extractor.extract_from_images(images)

    assert call_count["n"] == 3
    assert isinstance(result, InvoiceExtraction)
    assert result.invoice_meta.get("original_language") == "en"


@pytest.mark.asyncio
async def test_gemini_invalid_key_returns_error(monkeypatch: pytest.MonkeyPatch):
    from .conftest import make_jpeg_bytes

    class FakeModel:
        def generate_content(self, parts):
            raise Exception("401 Unauthorized")

    monkeypatch.setattr(gemini_service.genai, "GenerativeModel", lambda _: FakeModel())

    extractor = GeminiInvoiceExtractor(api_key="dummy", model_name="fake")
    images = make_images(make_jpeg_bytes())

    with pytest.raises(UploadValidationError):
        await extractor.extract_from_images(images)

