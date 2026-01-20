from datetime import date, datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from digido_digital_assistant.config import settings
from digido_digital_assistant.repositories.summaries import (
    fetch_latest_summary,
    insert_daily_summary,
)
from digido_digital_assistant.repositories.user_prefs import (
    fetch_user_prefs_by_id,
    update_summary_last_sent_on,
)
from digido_digital_assistant.services.finance.ingest_orchestrator import ingest_csv
from digido_digital_assistant.services.notifications import send_sms
from digido_digital_assistant.services.summaries import generate_daily_summary
from digido_digital_assistant.utils.time import to_local_time
from digido_digital_assistant.worker import run_due_summaries

router = APIRouter()


class SummaryRequest(BaseModel):
    user_id: str
    summary_date: date | None = None
    send_notifications: bool = False


class FinanceIngestRequest(BaseModel):
    """
    Request payload for finance statement CSV ingestion.

    Expected CSV columns:
    - transaction_date (or date): Date of the transaction (YYYY-MM-DD, MM/DD/YYYY, etc.)
    - description (or memo): Transaction description
    - amount: Transaction amount (can include $ and commas)
    - reference_id (optional): Unique identifier for the transaction
    - category (optional): Transaction category
    """

    user_id: str = Field(..., description="ID of the user uploading the statement")
    csv_content: str = Field(..., description="Raw CSV content as a string")


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


def _require_job_token(provided_token: str | None) -> None:
    if not settings.job_trigger_token:
        return
    if provided_token != settings.job_trigger_token:
        raise HTTPException(status_code=401, detail="Invalid job token")


@router.post("/v1/jobs/daily-summaries")
def run_daily_summary_job(x_job_token: str | None = Header(default=None)) -> dict:
    _require_job_token(x_job_token)
    run_due_summaries()
    return {"status": "ok"}


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

    if (
        request.send_notifications
        and "sms" in user.delivery_channels
        and user.phone_number
    ):
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


@router.post("/v1/finance/ingest")
def finance_ingest(request: FinanceIngestRequest) -> dict:
    """
    Ingest a CSV file containing finance statement records.

    Parses the CSV content, validates records, and persists valid transactions.
    Returns a summary of the ingestion including success/error counts.
    """
    if not request.csv_content.strip():
        raise HTTPException(status_code=400, detail="CSV content is empty")

    result = ingest_csv(request.user_id, request.csv_content)

    # Return 200 for successful or partial success, 400 only if all records failed
    if result.total_records > 0 and result.success_count == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "All records failed validation",
                "ingest_id": str(result.ingest_id),
                "timestamp": result.timestamp.isoformat(),
                "total_records": result.total_records,
                "success_count": result.success_count,
                "error_count": result.error_count,
                "errors": [
                    {
                        "row_number": e.row_number,
                        "field": e.field,
                        "message": e.message,
                    }
                    for e in result.errors
                ],
            },
        )

    return {
        "ingest_id": str(result.ingest_id),
        "timestamp": result.timestamp.isoformat(),
        "total_records": result.total_records,
        "success_count": result.success_count,
        "error_count": result.error_count,
        "errors": [
            {
                "row_number": e.row_number,
                "field": e.field,
                "message": e.message,
            }
            for e in result.errors
        ],
    }
