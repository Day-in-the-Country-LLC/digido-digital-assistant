from datetime import date
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


class SummaryState(TypedDict):
    user_id: str
    summary_date: date
    context: dict[str, Any]
    summary: str


def fetch_context(state: SummaryState) -> dict[str, Any]:
    # TODO: replace with MCP tools, calendar, tasks, and app signals.
    return {"context": {"items": []}}


def draft_summary(state: SummaryState) -> dict[str, Any]:
    summary_date = state["summary_date"]
    summary = (
        f"Daily summary for {state['user_id']} on {summary_date.isoformat()}: "
        "No context sources are wired up yet."
    )
    return {"summary": summary}


def _build_graph():
    graph = StateGraph(SummaryState)
    graph.add_node("fetch_context", fetch_context)
    graph.add_node("draft_summary", draft_summary)
    graph.set_entry_point("fetch_context")
    graph.add_edge("fetch_context", "draft_summary")
    graph.add_edge("draft_summary", END)
    return graph.compile()


_graph = _build_graph()


def run_daily_summary(user_id: str, summary_date: date) -> str:
    result = _graph.invoke(
        {
            "user_id": user_id,
            "summary_date": summary_date,
            "context": {},
            "summary": "",
        }
    )
    return result["summary"]
