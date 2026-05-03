from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InvoiceExtraction(BaseModel):
    """
    Flexible schema for invoice extraction.

    Gemini can return arbitrary keys inside seller/buyer/etc; we validate types but allow unknown fields.
    """

    model_config = ConfigDict(extra="allow")

    invoice_meta: dict[str, Any] = Field(default_factory=dict)
    seller: dict[str, Any] = Field(default_factory=dict)
    buyer: dict[str, Any] = Field(default_factory=dict)
    line_items: list[dict[str, Any]] = Field(default_factory=list)
    totals: dict[str, Any] = Field(default_factory=dict)
    payment: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
    other: dict[str, Any] = Field(default_factory=dict)

    @field_validator("notes", mode="before")
    @classmethod
    def _coerce_notes(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)

    @field_validator("invoice_meta", "seller", "buyer", "totals", "payment", "other", mode="before")
    @classmethod
    def _coerce_dicts(cls, v: Any) -> dict[str, Any]:
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        # If Gemini returns something unexpected, keep it under `other`.
        return {"_invalid_type": v}

    @field_validator("line_items", mode="before")
    @classmethod
    def _coerce_line_items(cls, v: Any) -> list[dict[str, Any]]:
        if v is None:
            return []
        if not isinstance(v, list):
            return []
        coerced: list[dict[str, Any]] = []
        for item in v:
            if isinstance(item, dict):
                coerced.append(item)
            else:
                coerced.append({"_invalid_type": item})
        return coerced

