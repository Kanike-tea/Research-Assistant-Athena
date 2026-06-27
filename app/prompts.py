"""Prompt templates for each research sub-task."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


# ── Explanation chain prompt ─────────────────────────────────────────────────

EXPLANATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a senior research analyst who writes thorough, well-structured "
            "explanations. Your output MUST be formatted in **Markdown** with clear "
            "headings (##), bullet points, and bold key terms. Cover the following "
            "aspects when relevant:\n"
            "- Definition and core concepts\n"
            "- Historical background and evolution\n"
            "- Key principles and mechanisms\n"
            "- Real-world applications and significance\n"
            "- Current trends and future outlook\n\n"
            "Write at an advanced-undergraduate level. Be precise yet accessible.",
        ),
        (
            "human",
            "Provide a detailed explanation of the following topic:\n\n{topic}",
        ),
    ]
)


# ── Summary chain prompt ────────────────────────────────────────────────────

SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert summariser. Distil the essence of any topic into "
            "exactly 2-3 clear, informative sentences. The summary must be "
            "self-contained — a reader with no prior knowledge should grasp the "
            "core idea immediately. Do NOT use bullet points or headings.",
        ),
        (
            "human",
            "Write a concise summary of the following topic:\n\n{topic}",
        ),
    ]
)


# ── Keywords chain prompt ───────────────────────────────────────────────────

KEYWORDS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a research indexing specialist. Extract the most important "
            "keywords and key-phrases for the given topic.\n\n"
            "Rules:\n"
            "- Return between 5 and 15 keywords.\n"
            "- Output ONLY a JSON array of strings — no preamble, no explanation.\n"
            '- Example output: ["keyword1", "keyword2", "keyword3"]\n'
            "- Order keywords from most to least relevant.",
        ),
        (
            "human",
            "Extract the most important keywords for this topic:\n\n{topic}",
        ),
    ]
)


# ── Category chain prompt ───────────────────────────────────────────────────

CATEGORY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an academic classification expert. Assign a single, broad "
            "academic or professional category to the given topic.\n\n"
            "Rules:\n"
            "- Return ONLY the category name — no explanation, no extra text.\n"
            "- Use established academic disciplines or professional fields "
            "(e.g., Computer Science, Medicine, Economics, Environmental Science, "
            "Political Science, Engineering, Psychology, etc.).\n"
            "- If the topic spans multiple fields, choose the most dominant one.",
        ),
        (
            "human",
            "Classify the following topic into a single category:\n\n{topic}",
        ),
    ]
)
