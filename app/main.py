"""FastAPI application – Research Assistant API."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.chains import run_research
from app.config import GOOGLE_API_KEY
from app.models import ResearchRequest, ResearchResponse

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)
logger = logging.getLogger(__name__)


# ── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Research Assistant API",
    description=(
        "Takes a topic string and produces four distinct outputs in parallel: "
        "a detailed explanation, a short summary, a list of important keywords, "
        "and a topic category — all powered by LangChain + Google Gemini."
    ),
    version="1.0.0",
)

# CORS – allow all origins during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup check ───────────────────────────────────────────────────────────

@app.on_event("startup")
async def _validate_config() -> None:
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "your-google-api-key-here":
        logger.warning(
            "⚠️  GOOGLE_API_KEY is not set. "
            "Copy .env.example → .env and add your key."
        )


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok"}


# ── Main research endpoint ──────────────────────────────────────────────────

@app.post(
    "/research",
    response_model=ResearchResponse,
    tags=["research"],
    summary="Analyse a research topic",
    description=(
        "Accepts a topic string and returns four parallel LLM outputs: "
        "a Markdown explanation, a concise summary, extracted keywords, "
        "and an academic category."
    ),
)
async def research(request: ResearchRequest) -> ResearchResponse:
    """Analyse the given topic using four parallel LangChain chains."""
    logger.info("📝 Research request received — topic: %r", request.topic)
    start = time.perf_counter()

    try:
        result = await run_research(request.topic)
    except Exception as exc:
        logger.exception("LLM pipeline failed for topic %r", request.topic)
        raise HTTPException(
            status_code=502,
            detail=f"The LLM pipeline encountered an error: {exc}",
        ) from exc

    elapsed = time.perf_counter() - start
    logger.info(
        "✅ Research complete — topic: %r, keywords: %d, time: %.2fs",
        request.topic,
        len(result["keywords"]),
        elapsed,
    )

    return ResearchResponse(**result)


# ── Frontend ────────────────────────────────────────────────────────────────

_STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the single-page frontend application."""
    return FileResponse(_STATIC_DIR / "index.html")


# Mount static assets AFTER all routes so /docs, /health etc. are not shadowed
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
