from datetime import datetime, timezone

from digido_digital_assistant.services.supabase_client import get_supabase

CONNECTED_ACCOUNTS_TABLE = "connected_accounts"
GOOGLE_PROVIDER = "google"


def fetch_connected_account(user_id: str, provider_account_id: str) -> dict | None:
    supabase = get_supabase()
    response = (
        supabase.table(CONNECTED_ACCOUNTS_TABLE)
        .select("id, refresh_token")
        .eq("user_id", user_id)
        .eq("provider", GOOGLE_PROVIDER)
        .eq("provider_account_id", provider_account_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def upsert_connected_account(payload: dict) -> dict:
    supabase = get_supabase()
    payload = {
        **payload,
        "provider": GOOGLE_PROVIDER,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    response = (
        supabase.table(CONNECTED_ACCOUNTS_TABLE)
        .upsert(payload, on_conflict="user_id,provider,provider_account_id")
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else payload
