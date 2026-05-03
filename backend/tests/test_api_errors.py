from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_missing_file_error(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.routes import upload as upload_route

    class FakeExtractor:
        async def extract_from_images(self, images):
            return {}

    monkeypatch.setattr(upload_route, "get_gemini_extractor", lambda: FakeExtractor())

    resp = await client.post("/upload", json={})
    assert resp.status_code == 422
    assert resp.json()["status"] == "error"


@pytest.mark.asyncio
async def test_wrong_request_error(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from app.routes import upload as upload_route

    class FakeExtractor:
        async def extract_from_images(self, images):
            return {}

    monkeypatch.setattr(upload_route, "get_gemini_extractor", lambda: FakeExtractor())

    # Sending multipart without the "file" field.
    resp = await client.post("/upload", files={"wrong_field": ("x.txt", b"hello", "text/plain")})
    assert resp.status_code == 422
    assert resp.json()["status"] == "error"

