from __future__ import annotations

import asyncio
from typing import Optional

from app.services.gemini_service import GeminiInvoiceExtractor, build_gemini_extractor
from app.utils.config import settings


request_semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
_gemini_extractor: Optional[GeminiInvoiceExtractor] = None


def get_gemini_extractor() -> GeminiInvoiceExtractor:
    global _gemini_extractor
    if _gemini_extractor is None:
        _gemini_extractor = build_gemini_extractor()
    return _gemini_extractor

