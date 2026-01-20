from datetime import date, datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from digido_digital_assistant.config import settings
from digido_digital_assistant.repositories.connected_accounts import (
    fetch_connected_account,
    upsert_connected_account,
)
from digido_digital_assistant.repositories.summaries import fetch_latest_summary, insert_daily_summary
from digido_digital_assistant.repositories.user_prefs import (
    fetch_user_prefs_by_id,
    update_summary_last_sent_on,
)
from digido_digital_assistant.services.google_oauth import (
    exchange_code,
    extract_account_info,
)
from digido_digital_assistant.services.notifications import send_sms
from digido_digital_assistant.services.summaries import generate_daily_summary
from digido_digital_assistant.services.supabase_auth import get_user_id_from_token
from digido_digital_assistant.utils.time import to_local_time
from digido_digital_assistant.worker import run_due_summaries

router = APIRouter()


class SummaryRequest(BaseModel):
    user_id: str
    summary_date: date | None = None
    send_notifications: bool = False


class GoogleOAuthExchangeRequest(BaseModel):
    user_id: str | None = None
    code: str
    code_verifier: str
    redirect_uri: str
    client_id: str


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


def _require_job_token(provided_token: str | None) -> None:
    if not settings.job_trigger_token:
        return
    if provided_token != settings.job_trigger_token:
        raise HTTPException(status_code=401, detail="Invalid job token")


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return authorization.split(" ", 1)[1]


def _validate_client_id(client_id: str) -> None:
    allowed = settings.google_oauth_client_ids
    if not allowed:
        return
    if client_id not in allowed:
        raise HTTPException(status_code=403, detail="Client ID not allowed")


@router.post("/v1/jobs/daily-summaries")
def run_daily_summary_job(x_job_token: str | None = Header(default=None)) -> dict:
    _require_job_token(x_job_token)
    run_due_summaries()
    return {"status": "ok"}


@router.post("/v1/oauth/google/exchange")
def exchange_google_oauth(
    request: GoogleOAuthExchangeRequest,
    authorization: str | None = Header(default=None),
) -> dict:
    access_token = _extract_bearer_token(authorization)
    try:
        user_id = get_user_id_from_token(access_token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    if request.user_id and request.user_id != user_id:
        raise HTTPException(status_code=403, detail="User mismatch")

    _validate_client_id(request.client_id)

    try:
        token_response = exchange_code(
            code=request.code,
            code_verifier=request.code_verifier,
            redirect_uri=request.redirect_uri,
            client_id=request.client_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    account_info = extract_account_info(token_response)
    if not account_info or not account_info.provider_account_id:
        raise HTTPException(status_code=400, detail="Unable to resolve Google account")

    existing = fetch_connected_account(user_id, account_info.provider_account_id)
    refresh_token = token_response.refresh_token or (existing.get("refresh_token") if existing else None)
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Missing refresh token; re-consent required")

    payload = {
        "user_id": user_id,
        "provider_account_id": account_info.provider_account_id,
        "email": account_info.email,
        "display_name": account_info.display_name,
        "access_token": token_response.access_token,
        "refresh_token": refresh_token,
        "token_expires_at": token_response.expires_at.isoformat() if token_response.expires_at else None,
        "scopes": token_response.scopes or [],
    }
    stored = upsert_connected_account(payload)
    return {
        "provider_account_id": stored.get("provider_account_id"),
        "email": stored.get("email"),
        "display_name": stored.get("display_name"),
    }


@router.post("/v1/summaries/run")
def run_summary(request: SummaryRequest) -> dict:
    user = fetch_user_prefs_by_id(request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User prefs not found")

    summary_date = request.summary_date
    if not summary_date:
        local_now = to_local_time(user.timezone, datetime.now(timezone.utc))
        summary_date = local_now.date()

    summary = generate_daily_summary(request.user_id, summary_date)
    insert_daily_summary(summary)
    update_summary_last_sent_on(request.user_id, summary_date)

    if request.send_notifications and "sms" in user.delivery_channels and user.phone_number:
        send_sms(user.phone_number, summary.content)

    return {
        "user_id": summary.user_id,
        "summary_date": summary.summary_date.isoformat(),
        "content": summary.content,
    }


@router.get("/v1/summaries/latest/{user_id}")
def latest_summary(user_id: str) -> dict:
    summary = fetch_latest_summary(user_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return {
        "user_id": summary.user_id,
        "summary_date": summary.summary_date.isoformat(),
        "content": summary.content,
    }
