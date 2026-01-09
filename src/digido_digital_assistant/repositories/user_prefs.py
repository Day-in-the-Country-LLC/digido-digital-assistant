from datetime import date, datetime, time, timezone

from digido_digital_assistant.models import UserPrefs
from digido_digital_assistant.services.supabase_client import get_supabase

PREFS_TABLE = "assistant_user_prefs"


def _parse_time(value: str | None) -> time:
    if not value:
        return time(hour=8, minute=0)
    return time.fromisoformat(value)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _build_user_prefs(row: dict) -> UserPrefs:
    return UserPrefs(
        user_id=str(row["user_id"]),
        timezone=row.get("timezone") or "UTC",
        summary_time=_parse_time(row.get("summary_time")),
        summary_enabled=bool(row.get("summary_enabled", True)),
        delivery_channels=list(row.get("delivery_channels") or []),
        phone_number=row.get("phone_number"),
        summary_last_sent_on=_parse_date(row.get("summary_last_sent_on")),
    )


def fetch_user_prefs(limit: int | None = None) -> list[UserPrefs]:
    supabase = get_supabase()
    query = supabase.table(PREFS_TABLE).select(
        "user_id, timezone, summary_time, summary_enabled, delivery_channels, phone_number, summary_last_sent_on"
    )
    if limit:
        query = query.limit(limit)
    response = query.execute()
    rows = response.data or []
    return [_build_user_prefs(row) for row in rows]


def fetch_user_prefs_by_id(user_id: str) -> UserPrefs | None:
    supabase = get_supabase()
    response = (
        supabase.table(PREFS_TABLE)
        .select(
            "user_id, timezone, summary_time, summary_enabled, delivery_channels, phone_number, summary_last_sent_on"
        )
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return None
    return _build_user_prefs(rows[0])


def update_summary_last_sent_on(user_id: str, summary_date: date) -> None:
    supabase = get_supabase()
    supabase.table(PREFS_TABLE).update(
        {
            "summary_last_sent_on": summary_date.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("user_id", user_id).execute()
