from __future__ import annotations

import io
from typing import AsyncIterator

import pytest
from httpx import AsyncClient

from app.schemas.invoice import InvoiceExtraction
from app.utils.config import settings


class FakeExtractor:
    async def extract_from_images(self, images: AsyncIterator) -> InvoiceExtraction:
        # Fully consume the stream to mimic real extraction behavior.
        async for _ in images:
            pass
        return InvoiceExtraction()


@pytest.mark.asyncio
async def test_valid_file_upload_success(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.routes import upload as upload_route

    async def fake_get_gemini_extractor():
        return FakeExtractor()

    monkeypatch.setattr(upload_route, "get_gemini_extractor", lambda: FakeExtractor())

    # Multi-page PDF should validate and process.
    from .conftest import make_pdf_bytes

    pdf_bytes = make_pdf_bytes(2)
    resp = await client.post(
        "/upload",
        files={"file": ("invoice.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["line_items"] == []


@pytest.mark.asyncio
async def test_unsupported_file_fail(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.routes import upload as upload_route

    monkeypatch.setattr(upload_route, "get_gemini_extractor", lambda: FakeExtractor())

    resp = await client.post(
        "/upload",
        files={"file": ("invoice.exe", b"not an allowed file", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert resp.json()["status"] == "error"


@pytest.mark.asyncio
async def test_empty_file_fail(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.routes import upload as upload_route

    monkeypatch.setattr(upload_route, "get_gemini_extractor", lambda: FakeExtractor())

    resp = await client.post(
        "/upload",
        files={"file": ("invoice.pdf", b"", "application/pdf")},
    )
    assert resp.status_code == 400
    assert resp.json()["status"] == "error"


@pytest.mark.asyncio
async def test_large_file_fail(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.routes import upload as upload_route

    monkeypatch.setattr(upload_route, "get_gemini_extractor", lambda: FakeExtractor())

    big_txt = b"a" * (settings.max_upload_mb * 1024 * 1024 + 1)
    resp = await client.post(
        "/upload",
        files={"file": ("invoice.txt", big_txt, "text/plain")},
    )
    assert resp.status_code == 400
    assert resp.json()["status"] == "error"

