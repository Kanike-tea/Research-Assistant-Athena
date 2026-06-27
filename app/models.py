"""Pydantic models for API request / response validation."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Request ──────────────────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    """Incoming request payload for the /research endpoint."""

    topic: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The research topic to analyse.",
        examples=["Quantum Computing"],
    )


# ── Response ─────────────────────────────────────────────────────────────────

class ResearchResponse(BaseModel):
    """Structured response returned by the /research endpoint."""

    topic: str = Field(
        ...,
        description="The original topic that was analysed.",
    )
    explanation: str = Field(
        ...,
        description="A detailed Markdown-formatted explanation of the topic.",
    )
    summary: str = Field(
        ...,
        description="A concise 2-3 sentence summary of the topic.",
    )
    keywords: list[str] = Field(
        ...,
        description="A list of important keywords / key-phrases related to the topic.",
    )
    category: str = Field(
        ...,
        description="A broad academic or professional category for the topic.",
    )
