"""FastAPI service exposing the public, knowledge-base driven resume."""

from __future__ import annotations

import hmac
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .generator import (
    Settings,
    build_document,
    load_snapshot,
    next_scheduled_at,
    write_snapshot,
)
from .models import ResumeDocument

SERVICE_NAME = "resume-assistant"
VERSION = "1.0.0"
CORS_ORIGINS = [
    "https://seres-ai.com",
    "http://127.0.0.1:8080",
    "http://localhost:8080",
]


def _expected_token(settings: Settings) -> Optional[str]:
    if settings.refresh_token:
        return settings.refresh_token
    token_file = settings.token_file
    if not token_file:
        return None
    try:
        token = Path(token_file).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return token or None


def _load_or_generate(app: FastAPI) -> ResumeDocument:
    settings: Settings = app.state.settings
    document = load_snapshot(settings)
    if document is not None:
        return document
    with app.state.lock:
        document = load_snapshot(settings)
        if document is not None:
            return document
        document = build_document(settings)
        write_snapshot(settings, document)
        return document


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or Settings.from_env()
    application = FastAPI(
        title="Resume Assistant API",
        description="由简历知识库生成的公开技术简历。",
        version=VERSION,
    )
    application.state.settings = settings
    application.state.lock = threading.Lock()
    application.state.last_refresh_at = None

    application.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @application.get("/api/resume/health")
    def health():
        return {"status": "ok", "service": SERVICE_NAME, "version": VERSION}

    @application.get("/api/resume/latest")
    def latest(request: Request):
        document = _load_or_generate(request.app)
        return JSONResponse(
            content=document.model_dump(),
            headers={"Cache-Control": "no-store"},
        )

    @application.get("/api/resume/status")
    def status(request: Request):
        document = _load_or_generate(request.app)
        payload = {
            "generated_at": document.generated_at,
            "source_hash": document.source.source_hash,
            "article_count": document.source.article_count,
            "kb_files": document.source.kb_files,
            "missing": document.missing,
            "next_scheduled_at": next_scheduled_at(),
        }
        return JSONResponse(content=payload, headers={"Cache-Control": "no-store"})

    @application.post("/api/resume/refresh")
    def refresh(request: Request):
        current_settings: Settings = request.app.state.settings
        provided = request.headers.get("X-Resume-Token") or ""
        expected = _expected_token(current_settings)
        if (
            not expected
            or not provided
            or not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
        ):
            raise HTTPException(status_code=401, detail="unauthorized")

        with request.app.state.lock:
            now = time.monotonic()
            last = request.app.state.last_refresh_at
            if last is not None and (now - last) < current_settings.rate_limit_seconds:
                raise HTTPException(status_code=429, detail="too_frequent")

            previous = load_snapshot(current_settings)
            previous_hash = previous.source.source_hash if previous else None
            try:
                document = build_document(current_settings)
                if previous is not None and document.generated_at <= previous.generated_at:
                    try:
                        moment = datetime.fromisoformat(previous.generated_at)
                        document.generated_at = (
                            moment + timedelta(seconds=1)
                        ).isoformat(timespec="seconds")
                    except ValueError:
                        pass
                write_snapshot(current_settings, document)
            except Exception as exc:  # keep the previous snapshot on failure
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "generation_failed",
                        "reason": f"{type(exc).__name__}: {exc}",
                    },
                )
            request.app.state.last_refresh_at = time.monotonic()
        return {
            "ok": True,
            "generated_at": document.generated_at,
            "changed": previous_hash != document.source.source_hash,
            "source_hash": document.source.source_hash,
        }

    return application


app = create_app()
