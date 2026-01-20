import base64
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from digido_digital_assistant.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GoogleTokenResponse:
    access_token: str
    refresh_token: str | None
    expires_at: datetime | None
    scopes: list[str]
    id_token: str | None


@dataclass(frozen=True)
class GoogleAccountInfo:
    provider_account_id: str
    email: str | None
    display_name: str | None


def _decode_jwt_payload(token: str) -> dict[str, Any] | None:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1]
        padded = payload + "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
        return json.loads(decoded.decode("utf-8"))
    except Exception:
        logger.exception("Failed to decode id_token payload")
        return None


def exchange_code(
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
    client_id: str,
) -> GoogleTokenResponse:
    payload = {
        "client_id": client_id,
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    if settings.google_oauth_client_secret:
        payload["client_secret"] = settings.google_oauth_client_secret

    response = httpx.post(settings.google_oauth_token_url, data=payload, timeout=15.0)
    response.raise_for_status()
    data = response.json()

    expires_at = None
    expires_in = data.get("expires_in")
    if expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    scopes = []
    if data.get("scope"):
        scopes = [item for item in data["scope"].split(" ") if item]

    return GoogleTokenResponse(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_at=expires_at,
        scopes=scopes,
        id_token=data.get("id_token"),
    )


def refresh_access_token(*, refresh_token: str, client_id: str) -> GoogleTokenResponse:
    payload = {
        "client_id": client_id,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    if settings.google_oauth_client_secret:
        payload["client_secret"] = settings.google_oauth_client_secret

    response = httpx.post(settings.google_oauth_token_url, data=payload, timeout=15.0)
    response.raise_for_status()
    data = response.json()

    expires_at = None
    expires_in = data.get("expires_in")
    if expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    scopes = []
    if data.get("scope"):
        scopes = [item for item in data["scope"].split(" ") if item]

    return GoogleTokenResponse(
        access_token=data["access_token"],
        refresh_token=refresh_token,
        expires_at=expires_at,
        scopes=scopes,
        id_token=data.get("id_token"),
    )


def fetch_userinfo(access_token: str) -> GoogleAccountInfo | None:
    headers = {"Authorization": f"Bearer {access_token}"}
    response = httpx.get(settings.google_oauth_userinfo_url, headers=headers, timeout=10.0)
    if response.status_code >= 400:
        logger.warning("Userinfo request failed: %s", response.text)
        return None
    data = response.json()
    return GoogleAccountInfo(
        provider_account_id=str(data.get("sub")),
        email=data.get("email"),
        display_name=data.get("name"),
    )


def extract_account_info(token_response: GoogleTokenResponse) -> GoogleAccountInfo | None:
    if token_response.id_token:
        payload = _decode_jwt_payload(token_response.id_token)
        if payload and payload.get("sub"):
            return GoogleAccountInfo(
                provider_account_id=str(payload.get("sub")),
                email=payload.get("email"),
                display_name=payload.get("name"),
            )
    return fetch_userinfo(token_response.access_token)
