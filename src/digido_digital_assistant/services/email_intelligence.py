from __future__ import annotations

import re
from typing import Any, Iterable, TypedDict


class ActionPlan(TypedDict):
    type: str
    reason: str
    confidence: float
    payload: dict[str, Any]
    requires_review: bool


class ActionResult(TypedDict):
    type: str
    status: str
    details: dict[str, Any]


NEWSLETTER_HINTS = (
    "newsletter",
    "digest",
    "substack",
    "medium",
    "read time",
    "top stories",
)

CALENDAR_HINTS = (
    "invite",
    "calendar",
    "meeting",
    "appointment",
    "schedule",
    "reservation",
    "event",
)

DISCOUNT_HINTS = (
    "promo code",
    "coupon",
    "discount",
    "use code",
    "save",
    "deal",
)

REPLY_HINTS = (
    "please reply",
    "let me know",
    "can you",
    "could you",
    "need your",
    "?",
)

TOPIC_FOLDERS: dict[str, tuple[str, ...]] = {
    "Articles": ("newsletter", "digest", "read", "blog", "article"),
    "Shopping": ("sale", "deal", "promo", "discount", "shop", "order"),
    "Travel": ("flight", "hotel", "trip", "booking", "reservation"),
    "Finance": ("invoice", "receipt", "statement", "payment"),
}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _email_text(email: dict[str, Any]) -> str:
    subject = email.get("subject") or ""
    snippet = email.get("snippet") or ""
    body = email.get("body") or email.get("plain_text") or ""
    return "\n".join(part for part in (subject, snippet, body) if part)


def build_summary(email: dict[str, Any]) -> str:
    sender = email.get("from") or email.get("sender") or "Unknown sender"
    subject = email.get("subject") or "No subject"
    snippet = email.get("snippet") or ""
    if snippet:
        return f"{sender}: {subject}. {snippet}".strip()
    return f"{sender}: {subject}."


def extract_links(text: str) -> list[str]:
    links = re.findall(r"https?://[^\s)>]+", text)
    clean_links = []
    for link in links:
        clean_links.append(link.rstrip(").,;!"))
    return list(dict.fromkeys(clean_links))


def extract_discount_codes(text: str) -> list[str]:
    patterns = [
        r"(?:promo|discount|coupon)\s*code[:\s]+([A-Z0-9]{4,})",
        r"use\s+code\s+([A-Z0-9]{4,})",
        r"code[:\s]+([A-Z0-9]{4,})",
    ]
    codes: list[str] = []
    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        codes.extend(match.upper() for match in matches)
    return list(dict.fromkeys(codes))


def extract_dates(text: str) -> list[str]:
    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    ]
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    return list(dict.fromkeys(matches))


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    norm = _normalize_text(text)
    return any(term in norm for term in terms)


def infer_folder(text: str, sender_domain: str | None) -> str:
    norm = _normalize_text(text)
    for folder, terms in TOPIC_FOLDERS.items():
        if any(term in norm for term in terms):
            return folder
    if sender_domain:
        return sender_domain.split(".")[0]
    return "Unsorted"


def plan_actions(email: dict[str, Any], summary: str, artifacts: dict[str, Any]) -> list[ActionPlan]:
    text = _email_text(email)
    norm_text = _normalize_text(text)
    sender_domain = email.get("sender_domain")
    if not sender_domain:
        sender = email.get("from") or email.get("sender") or ""
        match = re.search(r"@([^\s>]+)", sender)
        if match:
            sender_domain = match.group(1)

    actions: list[ActionPlan] = []

    discount_codes = artifacts.get("discount_codes", [])
    dates = artifacts.get("dates", [])
    links = artifacts.get("links", [])
    attachments = email.get("attachments") or []

    if discount_codes or _contains_any(norm_text, DISCOUNT_HINTS):
        actions.append(
            {
                "type": "store_discount",
                "reason": "Detected discount language or codes.",
                "confidence": 0.65 if discount_codes else 0.4,
                "payload": {"codes": discount_codes, "summary": summary},
                "requires_review": not bool(discount_codes),
            }
        )

    if dates or _contains_any(norm_text, CALENDAR_HINTS):
        actions.append(
            {
                "type": "create_calendar_event",
                "reason": "Detected date/event signals.",
                "confidence": 0.55 if dates else 0.35,
                "payload": {"dates": dates, "summary": summary},
                "requires_review": True,
            }
        )

    if _contains_any(norm_text, NEWSLETTER_HINTS) or len(links) >= 3:
        actions.append(
            {
                "type": "save_article",
                "reason": "Newsletter-style content or multiple links detected.",
                "confidence": 0.6,
                "payload": {
                    "folder": infer_folder(text, sender_domain),
                    "links": links,
                    "summary": summary,
                },
                "requires_review": False,
            }
        )

    if attachments:
        attachment_ids = []
        for attachment in attachments:
            if isinstance(attachment, dict) and attachment.get("attachment_id"):
                attachment_ids.append(attachment["attachment_id"])
        actions.append(
            {
                "type": "save_attachments",
                "reason": "Email includes attachments.",
                "confidence": 0.7 if attachment_ids else 0.4,
                "payload": {"attachment_ids": attachment_ids},
                "requires_review": not bool(attachment_ids),
            }
        )

    if _contains_any(norm_text, REPLY_HINTS):
        actions.append(
            {
                "type": "draft_reply",
                "reason": "Email appears to request a response.",
                "confidence": 0.4,
                "payload": {"summary": summary},
                "requires_review": True,
            }
        )

    actions.append(
        {
            "type": "mark_read",
            "reason": "Processed by the assistant.",
            "confidence": 0.9,
            "payload": {},
            "requires_review": False,
        }
    )

    return actions
