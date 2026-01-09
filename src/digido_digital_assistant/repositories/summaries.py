from datetime import date

from digido_digital_assistant.models import SummaryResult
from digido_digital_assistant.services.supabase_client import get_supabase

SUMMARY_TABLE = "assistant_daily_summaries"


def insert_daily_summary(summary: SummaryResult) -> None:
    supabase = get_supabase()
    supabase.table(SUMMARY_TABLE).insert(
        {
            "user_id": summary.user_id,
            "summary_date": summary.summary_date.isoformat(),
            "content": summary.content,
        }
    ).execute()


def fetch_latest_summary(user_id: str) -> SummaryResult | None:
    supabase = get_supabase()
    response = (
        supabase.table(SUMMARY_TABLE)
        .select("user_id, summary_date, content")
        .eq("user_id", user_id)
        .order("summary_date", desc=True)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return None
    row = rows[0]
    return SummaryResult(
        user_id=str(row["user_id"]),
        summary_date=date.fromisoformat(row["summary_date"]),
        content=row["content"],
    )
