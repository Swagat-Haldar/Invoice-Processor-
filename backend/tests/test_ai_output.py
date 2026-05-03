from __future__ import annotations

from typing import AsyncIterator

import pytest

from app.schemas.invoice import InvoiceExtraction
from app.services.gemini_service import GeminiInvoiceExtractor
from app.services import gemini_service
from app.services.file_processing import ImageBytes


def make_images(jpeg_bytes: bytes) -> AsyncIterator[ImageBytes]:
    async def _iter():
        yield ImageBytes(data=jpeg_bytes, mime_type="image/jpeg")

    return _iter()


@pytest.mark.asyncio
async def test_ai_output_valid_json_success(monkeypatch: pytest.MonkeyPatch):
    from .conftest import make_jpeg_bytes

    class FakeResponse:
        def __init__(self, text: str):
            self.text = text

    class FakeModel:
        def generate_content(self, parts):
            # Includes only a subset of keys.
            return FakeResponse(
                text=(
                    '{"invoice_meta":{"original_language":"fr"},'
                    '"seller":{"name":"Vendeur"},'
                    '"buyer":{},'
                    '"line_items":[],"totals":{},'
                    '"payment":{},"notes":"","other":{}}'
                )
            )

    monkeypatch.setattr(gemini_service.genai, "GenerativeModel", lambda _: FakeModel())

    extractor = GeminiInvoiceExtractor(api_key="dummy", model_name="fake")
    result: InvoiceExtraction = await extractor.extract_from_images(make_images(make_jpeg_bytes()))

    assert result.invoice_meta.get("original_language") == "fr"
    assert result.seller.get("name") == "Vendeur"


@pytest.mark.asyncio
async def test_ai_output_invalid_json_is_handled(monkeypatch: pytest.MonkeyPatch):
    from .conftest import make_jpeg_bytes

    class FakeResponse:
        def __init__(self, text: str):
            self.text = text

    class FakeModel:
        def generate_content(self, parts):
            return FakeResponse(text="not json at all")

    monkeypatch.setattr(gemini_service.genai, "GenerativeModel", lambda _: FakeModel())

    extractor = GeminiInvoiceExtractor(api_key="dummy", model_name="fake")
    result: InvoiceExtraction = await extractor.extract_from_images(make_images(make_jpeg_bytes()))

    assert isinstance(result, InvoiceExtraction)
    assert "_parse_error" in (result.other or {})


@pytest.mark.asyncio
async def test_ai_output_missing_fields_defaults_applied(monkeypatch: pytest.MonkeyPatch):
    from .conftest import make_jpeg_bytes

    class FakeResponse:
        def __init__(self, text: str):
            self.text = text

    class FakeModel:
        def generate_content(self, parts):
            # Missing seller/buyer/totals/payment/notes/other keys.
            return FakeResponse(text='{"line_items":[{"description":"A","quantity":"2"}]}')

    monkeypatch.setattr(gemini_service.genai, "GenerativeModel", lambda _: FakeModel())

    extractor = GeminiInvoiceExtractor(api_key="dummy", model_name="fake")
    result: InvoiceExtraction = await extractor.extract_from_images(make_images(make_jpeg_bytes()))

    assert result.invoice_meta == {}  # default
    assert result.seller == {}  # default
    assert result.buyer == {}  # default
    assert result.totals == {}  # default
    assert result.payment == {}  # default
    assert result.notes == ""  # default
    assert isinstance(result.line_items, list)
    assert result.line_items[0].get("description") == "A"

