import logging
from functools import lru_cache
from typing import Iterable

from twilio.rest import Client

from digido_digital_assistant.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_twilio_client() -> Client | None:
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("Twilio credentials missing; SMS/MMS disabled.")
        return None
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def send_sms(to_number: str, body: str, media_urls: Iterable[str] | None = None) -> str | None:
    client = get_twilio_client()
    if not client:
        return None
    if not settings.twilio_from_number:
        raise RuntimeError("TWILIO_FROM_NUMBER is not configured.")

    message = client.messages.create(
        to=to_number,
        from_=settings.twilio_from_number,
        body=body,
        media_url=list(media_urls) if media_urls else None,
    )
    return message.sid
