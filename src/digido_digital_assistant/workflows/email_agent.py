from __future__ import annotations

import re
import tempfile
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from digido_digital_assistant.services.email_intelligence import (
    ActionPlan,
    ActionResult,
    build_summary,
    extract_dates,
    extract_discount_codes,
    extract_links,
    plan_actions,
)
from digido_digital_assistant.services.email_categorization import categorize_email
from digido_digital_assistant.services.toolbox import NullToolbox, Toolbox
from digido_digital_assistant.services.sender_categorization import SenderCategorizationBuffer


class EmailAgentState(TypedDict):
    user_id: str
    message_id: str
    execute_actions: bool
    categorize_with_llm: bool
    sender_category: str | None
    suggested_category: str | None
    suggested_confidence: float | None
    suggested_rationale: str | None
    email: dict[str, Any]
    summary: str
    artifacts: dict[str, Any]
    pending_actions: list[ActionPlan]
    current_action: ActionPlan | None
    results: list[ActionResult]
    errors: list[str]
    route: str | None


def _ensure_list(value: list[ActionResult] | None) -> list[ActionResult]:
    return list(value) if value else []


def _append_result(state: EmailAgentState, result: ActionResult) -> dict[str, Any]:
    results = _ensure_list(state.get("results"))
    results.append(result)
    return {"results": results}


def _extract_email_address(raw: str | None) -> str | None:
    if not raw:
        return None
    match = re.search(r"<([^>]+)>", raw)
    if match:
        return match.group(1)
    if re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", raw):
        return raw
    return None


def _build_graph(toolbox: Toolbox, categorization_buffer: SenderCategorizationBuffer | None) -> Any:
    def fetch_email(state: EmailAgentState) -> dict[str, Any]:
        if state.get("email"):
            return {}
        result = toolbox.get_gmail_message(state["user_id"], state["message_id"])
        if not result["ok"] or not result["data"]:
            errors = list(state.get("errors", []))
            errors.append(result.get("error") or "Failed to fetch email.")
            return {"errors": errors, "email": {}}
        data = result["data"]
        if "email" in data:
            email = dict(data["email"])
            email["attachments"] = data.get("attachments", [])
        else:
            email = dict(data)
        return {"email": email}

    def summarize_email(state: EmailAgentState) -> dict[str, Any]:
        email = state.get("email", {})
        text = "\n".join(
            part
            for part in (
                email.get("subject"),
                email.get("snippet"),
                email.get("body"),
            )
            if part
        )
        artifacts = {
            "links": extract_links(text),
            "discount_codes": extract_discount_codes(text),
            "dates": extract_dates(text),
        }
        summary = build_summary(email)
        return {"summary": summary, "artifacts": artifacts}

    def categorize_email_node(state: EmailAgentState) -> dict[str, Any]:
        if not state.get("categorize_with_llm", False):
            return {}
        try:
            result = categorize_email(state.get("email", {}), state.get("summary"))
        except Exception as exc:
            errors = list(state.get("errors", []))
            errors.append(f"Categorization failed: {exc}")
            return {"errors": errors}
        if not result:
            return {}
        return {
            "suggested_category": result["category"],
            "suggested_confidence": result["confidence"],
            "suggested_rationale": result["rationale"],
        }

    def plan_actions_node(state: EmailAgentState) -> dict[str, Any]:
        actions = plan_actions(state.get("email", {}), state.get("summary", ""), state.get("artifacts", {}))
        return {"pending_actions": actions}

    def controller(state: EmailAgentState) -> dict[str, Any]:
        pending = list(state.get("pending_actions", []))
        if not pending:
            return {"current_action": None, "route": "finalize"}
        current = pending.pop(0)
        return {"current_action": current, "pending_actions": pending, "route": current["type"]}

    def article_agent(state: EmailAgentState) -> dict[str, Any]:
        action = state.get("current_action") or {}
        payload = action.get("payload", {})
        folder_name = payload.get("folder", "Unsorted")
        summary = payload.get("summary", state.get("summary", ""))
        links = payload.get("links", [])
        if not state.get("execute_actions", False):
            return _append_result(
                state,
                {
                    "type": "save_article",
                    "status": "planned",
                    "details": {"folder": folder_name, "links": links},
                },
            )

        folder_result = toolbox.create_drive_folder(state["user_id"], folder_name)
        if not folder_result["ok"]:
            return _append_result(
                state,
                {
                    "type": "save_article",
                    "status": "error",
                    "details": {"error": folder_result.get("error")},
                },
            )

        folder_id = (folder_result.get("data") or {}).get("id")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=True) as handle:
            handle.write(f"# {folder_name}\n\n")
            handle.write(summary + "\n\n")
            if links:
                handle.write("Links:\n")
                for link in links:
                    handle.write(f"- {link}\n")
            handle.flush()
            upload_result = toolbox.upload_drive_file(
                state["user_id"],
                file_path=handle.name,
                file_name="email_summary.md",
                parent_id=folder_id,
                mime_type="text/markdown",
            )
        status = "uploaded" if upload_result["ok"] else "error"
        return _append_result(
            state,
            {
                "type": "save_article",
                "status": status,
                "details": {"folder_id": folder_id, "upload": upload_result},
            },
        )

    def calendar_agent(state: EmailAgentState) -> dict[str, Any]:
        action = state.get("current_action") or {}
        payload = action.get("payload", {})
        dates = payload.get("dates", [])
        if not dates:
            return _append_result(
                state,
                {
                    "type": "create_calendar_event",
                    "status": "needs_review",
                    "details": {"reason": "No dates parsed."},
                },
            )
        if not state.get("execute_actions", False):
            return _append_result(
                state,
                {
                    "type": "create_calendar_event",
                    "status": "planned",
                    "details": {"dates": dates, "summary": payload.get("summary")},
                },
            )
        return _append_result(
            state,
            {
                "type": "create_calendar_event",
                "status": "needs_review",
                "details": {"dates": dates, "summary": payload.get("summary")},
            },
        )

    def discount_agent(state: EmailAgentState) -> dict[str, Any]:
        action = state.get("current_action") or {}
        payload = action.get("payload", {})
        codes = payload.get("codes", [])
        status = "captured" if codes else "needs_review"
        return _append_result(
            state,
            {
                "type": "store_discount",
                "status": status,
                "details": {"codes": codes, "summary": payload.get("summary")},
            },
        )

    def reply_agent(state: EmailAgentState) -> dict[str, Any]:
        action = state.get("current_action") or {}
        email = state.get("email", {})
        to_address = _extract_email_address(email.get("reply_to") or email.get("from"))
        subject = email.get("subject") or "Re: your email"
        body = (
            "Thanks for the note! I reviewed the details and will follow up shortly.\n\n"
            f"Summary: {state.get('summary', '')}"
        )
        if not state.get("execute_actions", False):
            return _append_result(
                state,
                {
                    "type": "draft_reply",
                    "status": "planned",
                    "details": {"to": to_address, "subject": subject},
                },
            )
        if not to_address:
            return _append_result(
                state,
                {
                    "type": "draft_reply",
                    "status": "needs_review",
                    "details": {"reason": "No reply-to address found."},
                },
            )
        result = toolbox.create_gmail_draft(
            state["user_id"],
            to=to_address,
            subject=f"Re: {subject}",
            body=body,
        )
        status = "drafted" if result["ok"] else "error"
        return _append_result(
            state,
            {
                "type": "draft_reply",
                "status": status,
                "details": {"draft": result},
            },
        )

    def attachments_agent(state: EmailAgentState) -> dict[str, Any]:
        action = state.get("current_action") or {}
        payload = action.get("payload", {})
        attachment_ids = payload.get("attachment_ids", [])
        if not attachment_ids:
            return _append_result(
                state,
                {
                    "type": "save_attachments",
                    "status": "needs_review",
                    "details": {"reason": "No attachment IDs were parsed."},
                },
            )
        if not state.get("execute_actions", False):
            return _append_result(
                state,
                {
                    "type": "save_attachments",
                    "status": "planned",
                    "details": {"attachment_ids": attachment_ids},
                },
            )
        result = toolbox.save_gmail_attachments_to_drive(
            state["user_id"], state["message_id"], attachment_ids
        )
        status = "saved" if result["ok"] else "error"
        return _append_result(
            state,
            {
                "type": "save_attachments",
                "status": status,
                "details": {"result": result},
            },
        )

    def mark_read_agent(state: EmailAgentState) -> dict[str, Any]:
        if not state.get("execute_actions", False):
            return _append_result(
                state,
                {"type": "mark_read", "status": "planned", "details": {}},
            )
        result = toolbox.mark_gmail_as_read(state["user_id"], state["message_id"])
        status = "done" if result["ok"] else "error"
        return _append_result(
            state,
            {"type": "mark_read", "status": status, "details": {"result": result}},
        )

    def finalize(state: EmailAgentState) -> dict[str, Any]:
        if not categorization_buffer:
            return {}
        category = state.get("sender_category")
        if not category:
            return {}
        email = state.get("email", {})
        sender_email = _extract_email_address(email.get("from") or email.get("sender") or "")
        if not sender_email:
            return {}
        categorization_buffer.record(
            user_id=state["user_id"],
            sender_email=sender_email,
            sender_domain=email.get("sender_domain"),
            category=category,
            source="user",
        )
        return {}

    def route_action(state: EmailAgentState) -> str:
        return state.get("route") or "finalize"

    graph = StateGraph(EmailAgentState)
    graph.add_node("fetch_email", fetch_email)
    graph.add_node("summarize_email", summarize_email)
    graph.add_node("categorize_email", categorize_email_node)
    graph.add_node("plan_actions", plan_actions_node)
    graph.add_node("controller", controller)
    graph.add_node("article_agent", article_agent)
    graph.add_node("calendar_agent", calendar_agent)
    graph.add_node("discount_agent", discount_agent)
    graph.add_node("reply_agent", reply_agent)
    graph.add_node("attachments_agent", attachments_agent)
    graph.add_node("mark_read_agent", mark_read_agent)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("fetch_email")
    graph.add_edge("fetch_email", "summarize_email")
    graph.add_edge("summarize_email", "categorize_email")
    graph.add_edge("categorize_email", "plan_actions")
    graph.add_edge("plan_actions", "controller")
    graph.add_edge("article_agent", "controller")
    graph.add_edge("calendar_agent", "controller")
    graph.add_edge("discount_agent", "controller")
    graph.add_edge("reply_agent", "controller")
    graph.add_edge("attachments_agent", "controller")
    graph.add_edge("mark_read_agent", "controller")
    graph.add_edge("finalize", END)

    graph.add_conditional_edges(
        "controller",
        route_action,
        {
            "save_article": "article_agent",
            "create_calendar_event": "calendar_agent",
            "store_discount": "discount_agent",
            "draft_reply": "reply_agent",
            "save_attachments": "attachments_agent",
            "mark_read": "mark_read_agent",
            "finalize": "finalize",
        },
    )
    return graph.compile()


def run_email_agent(
    user_id: str,
    message_id: str,
    execute_actions: bool = False,
    categorize_with_llm: bool = True,
    toolbox: Toolbox | None = None,
    email_payload: dict[str, Any] | None = None,
    sender_category: str | None = None,
    categorization_buffer: SenderCategorizationBuffer | None = None,
) -> EmailAgentState:
    graph = _build_graph(toolbox or NullToolbox(), categorization_buffer)
    initial_state: EmailAgentState = {
        "user_id": user_id,
        "message_id": message_id,
        "execute_actions": execute_actions,
        "categorize_with_llm": categorize_with_llm,
        "sender_category": sender_category,
        "suggested_category": None,
        "suggested_confidence": None,
        "suggested_rationale": None,
        "email": email_payload or {},
        "summary": "",
        "artifacts": {},
        "pending_actions": [],
        "current_action": None,
        "results": [],
        "errors": [],
        "route": None,
    }
    return graph.invoke(initial_state)
