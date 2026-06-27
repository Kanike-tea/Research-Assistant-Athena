"""LangChain chains and the parallel research pipeline.

This module wires up four independent LangChain chains (explanation, summary,
keywords, category) and exposes a single `RunnableParallel` that executes
them concurrently via `ainvoke()`.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import GOOGLE_API_KEY, LLM_MODEL, LLM_TEMPERATURE
from app.prompts import (
    CATEGORY_PROMPT,
    EXPLANATION_PROMPT,
    KEYWORDS_PROMPT,
    SUMMARY_PROMPT,
)

logger = logging.getLogger(__name__)


# ── LLM instance ────────────────────────────────────────────────────────────

def _build_llm() -> ChatGoogleGenerativeAI:
    """Create a configured LLM instance."""
    return ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=LLM_TEMPERATURE,
        convert_system_message_to_human=True,
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
