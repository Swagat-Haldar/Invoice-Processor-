from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from app.routes.upload import router as upload_router
from app.schemas.errors import ErrorResponse
from app.utils.config import settings
from app.utils.logger import get_logger
from app.utils.rate_limiter import InMemoryRateLimiter
from app.utils.file_validation import UploadValidationError


logger = get_logger(__name__)

app = FastAPI(
    title="Invoice Processor API",
    version="1.0.0",
)

origins = settings.cors_allowed_origins
if origins.strip() == "*":
    cors_origins = ["*"]
else:
    cors_origins = [o.strip() for o in origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.rate_limiter = InMemoryRateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)

app.include_router(upload_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(UploadValidationError)
async def upload_validation_exception_handler(request: Request, exc: UploadValidationError):
    return JSONResponse(status_code=400, content=ErrorResponse(message=str(exc)).model_dump())


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content=ErrorResponse(message=str(exc)).model_dump())


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    status_code = exc.status_code
    return JSONResponse(
        status_code=status_code if status_code != HTTP_429_TOO_MANY_REQUESTS else 429,
        content=ErrorResponse(message=str(exc.detail)).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content=ErrorResponse(message="Internal server error.").model_dump())

