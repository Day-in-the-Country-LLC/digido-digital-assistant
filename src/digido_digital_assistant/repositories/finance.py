"""Repository for finance statement records."""

from uuid import UUID

from digido_digital_assistant.models import StatementRecord
from digido_digital_assistant.services.supabase_client import get_supabase

STATEMENTS_TABLE = "assistant_finance_statements"


def insert_statement_records(
    user_id: str, ingest_id: UUID, records: list[StatementRecord]
) -> None:
    """Insert parsed statement records into the database."""
    if not records:
        return

    supabase = get_supabase()
    rows = [
        {
            "user_id": user_id,
            "ingest_id": str(ingest_id),
            "transaction_date": record.transaction_date.isoformat(),
            "description": record.description,
            "amount": str(record.amount),
            "reference_id": record.reference_id,
            "category": record.category,
        }
        for record in records
    ]
    supabase.table(STATEMENTS_TABLE).insert(rows).execute()
