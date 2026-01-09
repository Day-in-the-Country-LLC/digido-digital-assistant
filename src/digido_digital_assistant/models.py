from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class UserPrefs:
    user_id: str
    timezone: str
    summary_time: time
    summary_enabled: bool
    delivery_channels: list[str]
    phone_number: str | None
    summary_last_sent_on: date | None


@dataclass(frozen=True)
class SummaryResult:
    user_id: str
    summary_date: date
    content: str
