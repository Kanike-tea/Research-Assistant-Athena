"""LangChain chains and the parallel research pipeline.

This module wires up four independent LangChain chains (explanation, summary,
keywords, category) and exposes a single `RunnableParallel` that executes
them concurrently via `ainvoke()`.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel
from langchain_ollama import ChatOllama

from app.config import settings
from app.prompts import (
    CATEGORY_PROMPT,
    EXPLANATION_PROMPT,
    KEYWORDS_PROMPT,
    SUMMARY_PROMPT,
)

logger = logging.getLogger(__name__)


# ── LLM instance ────────────────────────────────────────────────────────────

def _build_llm() -> ChatOllama:
    """Create a configured LLM instance."""
    return ChatOllama(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        base_url=settings.OLLAMA_BASE_URL,
    )


# ── Individual chains ───────────────────────────────────────────────────────

_str_parser = StrOutputParser()


def _build_explanation_chain():
    """Chain that produces a Markdown explanation."""
    return EXPLANATION_PROMPT | _build_llm() | _str_parser


def _build_summary_chain():
    """Chain that produces a short summary."""
    return SUMMARY_PROMPT | _build_llm() | _str_parser


def _build_keywords_chain():
    """Chain that returns a raw JSON-array string of keywords."""
    return KEYWORDS_PROMPT | _build_llm() | _str_parser


def _build_category_chain():
    """Chain that returns a single category label."""
    return CATEGORY_PROMPT | _build_llm() | _str_parser


# ── Parallel pipeline ───────────────────────────────────────────────────────

def build_research_pipeline() -> RunnableParallel:
    """Return a `RunnableParallel` that runs all four chains concurrently.

    The returned runnable expects ``{"topic": "..."}`` as input and produces a
    dict with keys ``explanation``, ``summary``, ``keywords``, ``category``.
    """
    return RunnableParallel(
        explanation=_build_explanation_chain(),
        summary=_build_summary_chain(),
        keywords=_build_keywords_chain(),
        category=_build_category_chain(),
    )


# ── Helper to post-process raw LLM output ───────────────────────────────────

def parse_keywords(raw: str) -> list[str]:
    """Best-effort parse of the keywords JSON array from the LLM response.

    Falls back to comma/newline splitting if JSON parsing fails.
    """
    text = raw.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(k).strip() for k in parsed if str(k).strip()]
    except (json.JSONDecodeError, TypeError):
        logger.warning("Keywords JSON parse failed – falling back to text split.")

    # Fallback: split on commas or newlines
    separators = "," if "," in text else "\n"
    return [
        k.strip().strip('"').strip("'").lstrip("- ")
        for k in text.split(separators)
        if k.strip()
    ]


async def run_research(topic: str) -> dict[str, Any]:
    """Execute the full research pipeline for the given *topic*.

    Returns a dict ready to be serialised into a ``ResearchResponse``.
    """
    pipeline = build_research_pipeline()
    raw_results: dict[str, str] = await pipeline.ainvoke({"topic": topic})

    return {
        "topic": topic,
        "explanation": raw_results["explanation"].strip(),
        "summary": raw_results["summary"].strip(),
        "keywords": parse_keywords(raw_results["keywords"]),
        "category": raw_results["category"].strip(),
    }


# ── Streaming pipeline (SSE) ───────────────────────────────────────────────

def _postprocess(key: str, raw: str) -> Any:
    """Apply per-key post-processing to raw LLM output."""
    if key == "keywords":
        return parse_keywords(raw)
    return raw.strip()


async def stream_research(topic: str) -> AsyncGenerator[tuple[str, Any], None]:
    """Yield ``(key, value)`` tuples as each chain completes independently.

    Unlike :func:`run_research` which waits for all four chains,
    this generator fires each chain as a separate ``asyncio.Task`` and
    yields results **the instant** each one finishes — enabling
    Server-Sent Events on the API layer.
    """
    import asyncio

    chains: dict[str, Any] = {
        "summary": _build_summary_chain(),
        "explanation": _build_explanation_chain(),
        "keywords": _build_keywords_chain(),
        "category": _build_category_chain(),
    }

    # Launch all chains concurrently as independent tasks
    task_to_key: dict[asyncio.Task, str] = {
        asyncio.create_task(chain.ainvoke({"topic": topic})): key
        for key, chain in chains.items()
    }

    # Yield results in completion order (fastest first)
    for coro in asyncio.as_completed(task_to_key.keys()):
        result = await coro
        # Resolve which key this completed task belongs to
        finished_task = None
        for task, key in task_to_key.items():
            if task.done() and not getattr(task, "_yielded", False):
                try:
                    if task.result() is result:
                        finished_task = task
                        break
                except Exception:
                    continue
        if finished_task is None:
            # Fallback: match by identity didn't work — iterate remaining
            continue
        finished_task._yielded = True  # type: ignore[attr-defined]
        key = task_to_key[finished_task]
        yield (key, _postprocess(key, result))
