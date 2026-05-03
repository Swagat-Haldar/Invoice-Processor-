from __future__ import annotations

from typing import AsyncIterator

import pytest
from httpx import AsyncClient

from app.schemas.invoice import InvoiceExtraction


class PageCountingExtractor:
    def __init__(self):
        self.called_with_pages = 0

    async def extract_from_images(self, images: AsyncIterator) -> InvoiceExtraction:
        count = 0
        async for _ in images:
            count += 1
        # Return a marker so we can assert conversion succeeded.
        return InvoiceExtraction(invoice_meta={"pages_processed": count})


@pytest.mark.asyncio
async def test_multi_page_pdf_processing_success(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.routes import upload as upload_route

    extractor = PageCountingExtractor()
    monkeypatch.setattr(upload_route, "get_gemini_extractor", lambda: extractor)

    from .conftest import make_pdf_bytes

    pdf_bytes = make_pdf_bytes(3)
    resp = await client.post(
        "/upload",
        files={"file": ("invoice.pdf", pdf_bytes, "application/pdf")},
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["invoice_meta"]["pages_processed"] == 3


@pytest.mark.asyncio
async def test_corrupted_file_fail(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.routes import upload as upload_route

    # Even with a fake extractor, conversion should fail before Gemini is invoked.
    monkeypatch.setattr(upload_route, "get_gemini_extractor", lambda: PageCountingExtractor())

    # Must start with %PDF to pass magic checks, but be structurally invalid.
    corrupted_pdf = b"%PDF-1.7\n" + b"x" * 5000
    resp = await client.post(
        "/upload",
        files={"file": ("invoice.pdf", corrupted_pdf, "application/pdf")},
    )

    assert resp.status_code == 400
    assert resp.json()["status"] == "error"

