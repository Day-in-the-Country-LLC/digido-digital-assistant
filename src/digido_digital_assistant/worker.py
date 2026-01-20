import logging
from datetime import date, datetime, timezone

from digido_digital_assistant.config import settings
from digido_digital_assistant.repositories.summaries import insert_daily_summary
from digido_digital_assistant.repositories.user_prefs import (
    fetch_user_prefs,
    fetch_user_prefs_by_id,
    update_summary_last_sent_on,
)
from digido_digital_assistant.services.notifications import send_sms
from digido_digital_assistant.services.summaries import generate_daily_summary
from digido_digital_assistant.utils.time import to_local_time

logger = logging.getLogger(__name__)


def _summary_due(local_now: datetime, summary_time) -> bool:
    return local_now.time() >= summary_time


def run_summary_for_user(
    user_id: str, summary_date: date, send_notifications: bool = True
) -> None:
    user = fetch_user_prefs_by_id(user_id)
    if not user:
        raise RuntimeError(f"User prefs not found for {user_id}")

    summary = generate_daily_summary(user_id, summary_date)
    insert_daily_summary(summary)
    update_summary_last_sent_on(user_id, summary_date)

    if send_notifications and "sms" in user.delivery_channels and user.phone_number:
        send_sms(user.phone_number, summary.content)


def run_due_summaries() -> None:
    now_utc = datetime.now(timezone.utc)
    users = fetch_user_prefs(limit=settings.summary_batch_limit)

    for user in users:
        if not user.summary_enabled:
            continue

        local_now = to_local_time(user.timezone, now_utc)
        local_date = local_now.date()

        if user.summary_last_sent_on == local_date:
            continue
        if not _summary_due(local_now, user.summary_time):
            continue

        logger.info("Running summary for %s (%s)", user.user_id, local_date)
        run_summary_for_user(user.user_id, local_date, send_notifications=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_due_summaries()


if __name__ == "__main__":
    main()
