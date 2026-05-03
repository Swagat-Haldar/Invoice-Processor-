from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.controllers.upload_controller import handle_upload
from app.dependencies import get_gemini_extractor, request_semaphore
from app.schemas.invoice import InvoiceExtraction
from app.utils.config import settings

router = APIRouter()


@router.post("/upload", response_model=InvoiceExtraction)
async def upload_invoice(request: Request, file: UploadFile = File(...)) -> InvoiceExtraction:
    # Basic in-memory rate limiting (future scope: Redis/queue-based).
    rate_limiter = request.app.state.rate_limiter
    client_ip = (request.client.host if request.client else None) or "anonymous"
    if not await rate_limiter.check(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    async with request_semaphore:
        gemini_extractor = get_gemini_extractor()
        invoice = await handle_upload(
            file=file,
            gemini_extractor=gemini_extractor,
            max_upload_mb=settings.max_upload_mb,
        )
        return invoice

