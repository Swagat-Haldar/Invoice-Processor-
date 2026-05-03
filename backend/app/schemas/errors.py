from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    message: str = Field(default="", description="Human-readable error message.")

