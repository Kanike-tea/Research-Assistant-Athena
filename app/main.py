"""FastAPI application – Research Assistant API."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.chains import run_research, stream_research
from app.models import ResearchRequest, ResearchResponse
from app.metrics import metrics

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
        "and a topic category — all powered by LangChain + Ollama."
    ),
    version="2.0.0",
)
@app.on_event("startup")
async def startup_event():
    logger.info("Research Assistant API started successfully.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Research Assistant API stopped.")

# CORS – allow all origins during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health_check():
    """Simple liveness probe."""

    logger.info("Health check endpoint called.")

    return {
        "status": "ok",
        "service": "Research Assistant API",
        "version": app.version,
    }

@app.get("/metrics", tags=["meta"])
async def get_metrics():
    """Return application metrics."""
    logger.info("Metrics endpoint called.")
    return metrics.get_metrics()

# ── Main research endpoint (batch) ─────────────────────────────────────────

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
        metrics.record_failure()
        logger.exception("LLM pipeline failed for topic %r", request.topic)
        raise HTTPException(
            status_code=502,
            detail=f"The LLM pipeline encountered an error: {exc}",
        ) from exc

    elapsed = time.perf_counter() - start
    metrics.record_success(elapsed)
    if elapsed > 5:
        logger.warning(
            "Slow research request detected: %.2f seconds for topic %r",
            elapsed,
            request.topic,
        )
    logger.info(
        "✅ Research complete — topic: %r, keywords: %d, time: %.2fs",
        request.topic,
        len(result["keywords"]),
        elapsed,
    )
    result["execution_time"] = round(elapsed, 2)
    return ResearchResponse(**result)
    

    


# ── Streaming research endpoint (SSE) ──────────────────────────────────────

@app.post(
    "/research/stream",
    tags=["research"],
    summary="Stream research results via SSE",
    description=(
        "Accepts a topic string and streams results as Server-Sent Events. "
        "Each chain result is sent the instant it completes. "
        "Event names: summary, explanation, keywords, category, done."
    ),
)
async def research_stream(request: ResearchRequest):
    """Stream research results as Server-Sent Events."""
    logger.info("📡 SSE stream request — topic: %r", request.topic)

    async def event_generator():
        start = time.perf_counter()
        try:
            async for key, value in stream_research(request.topic):
                payload = json.dumps({"key": key, "value": value}, ensure_ascii=False)
                yield f"event: {key}\ndata: {payload}\n\n"
                logger.info("  → Streamed: %s", key)
            elapsed = round(time.perf_counter() - start, 2)
            logger.info("Execution Time: %.2f seconds", elapsed)

            payload = json.dumps({"execution_time": elapsed})
            yield f"event: execution_time\ndata: {payload}\n\n"

            yield "event: done\ndata: {}\n\n"
            logger.info("✅ SSE stream complete — topic: %r", request.topic)
        except Exception as exc:
            error_payload = json.dumps({"error": str(exc)})
            yield f"event: error\ndata: {error_payload}\n\n"
            logger.exception("SSE stream failed for topic %r", request.topic)
            metrics.record_failure()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Frontend ────────────────────────────────────────────────────────────────

_STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the single-page frontend application."""
    logger.info("Serving frontend index.html")
    return FileResponse(_STATIC_DIR / "index.html")


# Mount static assets AFTER all routes so /docs, /health etc. are not shadowed
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

