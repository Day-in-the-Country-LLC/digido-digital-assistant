import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


def safe_zoneinfo(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except Exception:
        logger.warning("Invalid timezone '%s'; defaulting to UTC.", tz_name)
        return ZoneInfo("UTC")


def to_local_time(tz_name: str, now_utc: datetime) -> datetime:
    return now_utc.astimezone(safe_zoneinfo(tz_name))
