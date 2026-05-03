from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

import google.generativeai as genai
from PIL import Image

from app.services.file_processing import ImageBytes
from app.schemas.invoice import InvoiceExtraction
from app.utils.config import settings
from app.utils.circuit_breaker import CircuitBreaker
from app.utils.file_validation import UploadValidationError
from app.utils.gemini_parsing import safe_json_loads
from app.utils.logger import get_logger


logger = get_logger(__name__)

MASTER_PROMPT = """You are an expert invoice data extraction engine.

You will receive an invoice as an image (or rendered page).
Your job is to extract EVERY piece of information from this invoice.

Return ONLY valid JSON.

GLOBAL RULES:
- Extract maximum structured data
- Do NOT hallucinate
- Preserve original values exactly
- Missing fields → ""
- Uncertain fields → add '_confidence': 'low'
- Handle multilingual invoices
- Never omit useful data

STRUCTURE:

{
  "invoice_meta": {...},
  "seller": {...},
  "buyer": {...},
  "line_items": [...],
  "totals": {...},
  "payment": {...},
  "notes": "",
  "other": {}
}

EXTRA:
- Detect language → add "original_language"
- Unknown fields → "other"
- Maintain strict JSON

Return ONLY JSON."""


class GeminiInvoiceExtractor:
    def __init__(self, *, api_key: str, model_name: str):
        if not api_key:
            raise UploadValidationError("Missing Gemini API key.")
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name)
        self._breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            reset_timeout_s=settings.circuit_breaker_reset_timeout_s,
        )
        self._gemini_semaphore = asyncio.Semaphore(settings.max_concurrent_gemini_calls)

    async def extract_from_images(self, images: AsyncIterator[ImageBytes]) -> InvoiceExtraction:
        """
        Process pages sequentially and merge results.
        """
        base: InvoiceExtraction = InvoiceExtraction()

        idx = 0
        async for image in images:
            page_bytes, mime_type = image.data, image.mime_type
            # Safety: keep one page at a time for memory control.
            page_result = await self._extract_one_page(page_bytes=page_bytes, mime_type=mime_type)
            base = self._merge_invoice(base, page_result)
            logger.info("Processed page %s", idx + 1)
            idx += 1

        return base

    async def _extract_one_page(self, *, page_bytes: bytes, mime_type: str) -> InvoiceExtraction:
        # Convert bytes -> PIL image in a thread.
        pil_img = await asyncio.to_thread(self._bytes_to_pil, page_bytes)

        async with self._gemini_semaphore:
            raw_text: str = ""
            last_error: str | None = None

            for attempt in range(settings.gemini_retry_max_attempts):
                if not await self._breaker.allow_request():
                    last_error = "Gemini circuit breaker is open."
                    break

                try:
                    raw_text = await asyncio.wait_for(
                        asyncio.to_thread(self._call_gemini, pil_img),
                        timeout=settings.gemini_timeout_s,
                    )
                    await self._breaker.record_success()
                    parsed, parse_err = safe_json_loads(raw_text)
                    if parse_err:
                        logger.warning("Gemini JSON parse error: %s", parse_err)
                        return InvoiceExtraction(
                            other={"_raw_response": raw_text, "_parse_error": parse_err, "_page_bytes_mime": mime_type}
                        )
                    validated = InvoiceExtraction.model_validate(parsed)
                    return validated
                except Exception as e:
                    msg = str(e).lower()
                    # Authentication / permission issues are not retryable.
                    if any(x in msg for x in ["401", "403", "unauthorized", "forbidden", "permission denied"]):
                        raise UploadValidationError("Gemini authentication/permission failure.") from e

                    last_error = f"{type(e).__name__}: {e}"
                    logger.warning("Gemini call failed (attempt %s): %s", attempt + 1, last_error)
                    await self._breaker.record_failure()
                    if attempt >= settings.gemini_retry_max_attempts - 1:
                        break
                    await asyncio.sleep(settings.gemini_retry_base_delay_s * (2**attempt))

            logger.error("Gemini extraction failed: %s", last_error)
            return InvoiceExtraction(
                other={"_raw_response": raw_text, "_gemini_error": last_error, "_page_bytes_mime": mime_type}
            )

    def _bytes_to_pil(self, page_bytes: bytes) -> Image.Image:
        from PIL import Image as PILImage
        import io

        img = PILImage.open(io.BytesIO(page_bytes))
        img.load()
        return img

    def _call_gemini(self, pil_img: Image.Image) -> str:
        """
        Calls Gemini synchronously. Return response text.
        """
        response = self._model.generate_content([MASTER_PROMPT, pil_img])
        # SDK usually returns `response.text`.
        text = getattr(response, "text", None)
        if text is None:
            text = str(response)
        return text

    def _merge_invoice(self, base: InvoiceExtraction, new: InvoiceExtraction) -> InvoiceExtraction:
        merged = base.model_dump()

        # Merge dict-like top-level fields
        dict_fields = ["invoice_meta", "seller", "buyer", "totals", "payment", "other"]
        for field in dict_fields:
            base_dict = merged.get(field) or {}
            new_dict = getattr(new, field) or {}
            if not isinstance(base_dict, dict):
                base_dict = {}
            if not isinstance(new_dict, dict):
                new_dict = {}

            for k, v in new_dict.items():
                if k not in base_dict or base_dict[k] in ("", {}, None):
                    base_dict[k] = v
                else:
                    if base_dict[k] != v:
                        conflicts = merged.setdefault("other", {}).setdefault("_conflicts", [])
                        if isinstance(conflicts, list):
                            conflicts.append(
                                {
                                    "field": field,
                                    "key": k,
                                    "base": base_dict[k],
                                    "new": v,
                                }
                            )
            merged[field] = base_dict

        # Merge notes (concatenate when both exist)
        if getattr(new, "notes", ""):
            if merged.get("notes"):
                if str(merged["notes"]).strip() != str(new.notes).strip():
                    merged["notes"] = f"{merged['notes']}\n{new.notes}"
            else:
                merged["notes"] = new.notes

        # Merge line items
        if new.line_items:
            merged["line_items"] = (merged.get("line_items") or []) + new.line_items
            merged["line_items"] = self._dedupe_line_items(merged["line_items"])

        return InvoiceExtraction.model_validate(merged)

    def _dedupe_line_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            desc = str(item.get("description") or item.get("item") or item.get("name") or "")
            qty = str(item.get("quantity") or item.get("qty") or "")
            unit = str(item.get("unit_price") or item.get("unitPrice") or "")
            total = str(item.get("total_price") or item.get("totalPrice") or "")
            sig = f"{desc}||{qty}||{unit}||{total}"
            if sig in seen:
                continue
            seen.add(sig)
            out.append(item)
        return out


def build_gemini_extractor() -> GeminiInvoiceExtractor:
    return GeminiInvoiceExtractor(api_key=settings.gemini_api_key, model_name=settings.gemini_model)

