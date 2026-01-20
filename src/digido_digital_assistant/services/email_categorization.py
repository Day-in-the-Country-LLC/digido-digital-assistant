from __future__ import annotations

import json
import logging
from typing import Any, TypedDict

from digido_digital_assistant.config import settings
from digido_digital_assistant.services.openai_client import get_openai_client

logger = logging.getLogger(__name__)


class CategorizationResult(TypedDict):
    category: str
    confidence: float
    rationale: str


def _build_text(email: dict[str, Any], summary: str | None) -> str:
    parts = [
        email.get("subject"),
        email.get("snippet"),
        email.get("body"),
        summary,
    ]
    return "\n".join(part for part in parts if part)


def _normalize_categories(categories: list[str]) -> list[str]:
    clean = [cat.strip() for cat in categories if cat and cat.strip()]
    if "Other" not in clean:
        clean.append("Other")
    return clean


def categorize_email(
    email: dict[str, Any],
    summary: str | None = None,
    categories: list[str] | None = None,
) -> CategorizationResult | None:
    text = _build_text(email, summary)
    if not text:
        return None

    category_list = _normalize_categories(categories or settings.sender_categorization_categories)
    category_str = ", ".join(category_list)

    prompt = (
        "You categorize emails for a personal assistant. "
        "Choose exactly one category from this list: "
        f"{category_str}. "
        "Return JSON with keys: category, confidence, rationale. "
        "confidence must be a number between 0 and 1. "
        "If unsure, return category 'Other' with low confidence.\n\n"
        f"Email content:\n{text}"
    )

    client = get_openai_client()
    response = client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        temperature=settings.openai_temperature,
        messages=[
            {"role": "system", "content": "You are a helpful email categorization assistant."},
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content if response.choices else None
    if not content:
        return None

    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Failed to parse categorization response: %s", content)
        return None

    category = str(payload.get("category") or "Other")
    if category not in category_list:
        category = "Other"

    try:
        confidence = float(payload.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(0.0, min(1.0, confidence))
    rationale = str(payload.get("rationale") or "")

    return {"category": category, "confidence": confidence, "rationale": rationale}
