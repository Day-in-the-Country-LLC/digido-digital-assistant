import logging

from openai import OpenAI

from digido_digital_assistant.config import settings
from digido_digital_assistant.services.secret_manager import get_secret

logger = logging.getLogger(__name__)

_cached_api_key: str | None = None


def get_openai_api_key() -> str | None:
    global _cached_api_key
    if _cached_api_key:
        return _cached_api_key
    if settings.openai_api_key:
        _cached_api_key = settings.openai_api_key
        return _cached_api_key

    if settings.openai_api_key_secret_name:
        secret = get_secret(settings.openai_api_key_secret_name)
        if secret:
            _cached_api_key = secret
            return _cached_api_key

    logger.warning("OpenAI API key not configured.")
    return None


def get_openai_client() -> OpenAI:
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OpenAI API key not configured.")
    return OpenAI(api_key=api_key)
