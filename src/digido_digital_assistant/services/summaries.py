from datetime import date

from digido_digital_assistant.models import SummaryResult
from digido_digital_assistant.workflows.daily_summary import run_daily_summary


def generate_daily_summary(user_id: str, summary_date: date) -> SummaryResult:
    content = run_daily_summary(user_id, summary_date)
    return SummaryResult(user_id=user_id, summary_date=summary_date, content=content)
