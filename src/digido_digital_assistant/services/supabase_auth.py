from typing import Any

from digido_digital_assistant.services.supabase_client import get_supabase


def _extract_user_id(result: Any) -> str | None:
    if hasattr(result, "user"):
        user = result.user
        if hasattr(user, "id"):
            return user.id
        if isinstance(user, dict):
            return user.get("id")
    if isinstance(result, dict):
        user = result.get("user") or result.get("data", {}).get("user")
        if isinstance(user, dict):
            return user.get("id")
    return None


def get_user_id_from_token(access_token: str) -> str:
    supabase = get_supabase()
    result = supabase.auth.get_user(access_token)
    user_id = _extract_user_id(result)
    if not user_id:
        raise RuntimeError("Unable to resolve user from access token")
    return user_id
