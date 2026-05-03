from __future__ import annotations

import io
import os
import sys
from typing import AsyncIterator

import fitz
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from PIL import Image

# Ensure `app` package is importable when running from repo root or backend/.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.main import app as fastapi_app  # noqa: E402
from app.schemas.invoice import InvoiceExtraction  # noqa: E402
from app.services.file_processing import ImageBytes  # noqa: E402


@pytest.fixture
def app() -> FastAPI:
    return fastapi_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


def make_jpeg_bytes() -> bytes:
    img = Image.new("RGB", (800, 600), color="white")
    bio = io.BytesIO()
    img.save(bio, format="JPEG", quality=80)
    return bio.getvalue()


def make_pdf_bytes(num_pages: int) -> bytes:
    doc = fitz.open()
    for i in range(num_pages):
        doc.new_page()
        page = doc[i]
        page.insert_text((72, 72), f"Invoice Page {i + 1}", fontsize=12)
    return doc.tobytes()


async def image_bytes_iter(images: list[ImageBytes]) -> AsyncIterator[ImageBytes]:
    for img in images:
        yield img


def invoice_success_stub() -> InvoiceExtraction:
    return InvoiceExtraction(
        invoice_meta={"original_language": "en"},
        seller={"name": "Seller"},
        buyer={"name": "Buyer"},
        line_items=[{"description": "Item", "quantity": "1", "unit_price": "10", "total_price": "10"}],
        totals={"grand_total": "10"},
        payment={"method": "Cash"},
        notes="",
        other={},
    )

