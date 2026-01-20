"""Orchestrator for finance statement CSV ingestion."""

import csv
import io
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from digido_digital_assistant.models import IngestError, IngestResult, StatementRecord
from digido_digital_assistant.repositories.finance import insert_statement_records


def parse_date(value: str, row_number: int) -> tuple[date | None, IngestError | None]:
    """Parse a date string in various common formats."""
    value = value.strip()
    formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date(), None
        except ValueError:
            continue
    return None, IngestError(
        row_number=row_number,
        field="transaction_date",
        message=f"Invalid date format: '{value}'",
    )


def parse_amount(
    value: str, row_number: int
) -> tuple[Decimal | None, IngestError | None]:
    """Parse an amount string to Decimal."""
    value = value.strip().replace(",", "").replace("$", "")
    try:
        return Decimal(value), None
    except InvalidOperation:
        return None, IngestError(
            row_number=row_number,
            field="amount",
            message=f"Invalid amount format: '{value}'",
        )


def parse_csv_row(
    row: dict[str, str], row_number: int
) -> tuple[StatementRecord | None, list[IngestError]]:
    """Parse a single CSV row into a StatementRecord."""
    errors: list[IngestError] = []

    # Required: transaction_date
    date_str = row.get("transaction_date") or row.get("date") or ""
    if not date_str:
        errors.append(
            IngestError(
                row_number=row_number,
                field="transaction_date",
                message="Missing required field: transaction_date",
            )
        )
        transaction_date = None
    else:
        transaction_date, date_error = parse_date(date_str, row_number)
        if date_error:
            errors.append(date_error)

    # Required: description
    description = (row.get("description") or row.get("memo") or "").strip()
    if not description:
        errors.append(
            IngestError(
                row_number=row_number,
                field="description",
                message="Missing required field: description",
            )
        )

    # Required: amount
    amount_str = row.get("amount") or ""
    if not amount_str:
        errors.append(
            IngestError(
                row_number=row_number,
                field="amount",
                message="Missing required field: amount",
            )
        )
        amount = None
    else:
        amount, amount_error = parse_amount(amount_str, row_number)
        if amount_error:
            errors.append(amount_error)

    # Optional: reference_id
    reference_id = (
        row.get("reference_id") or row.get("ref") or row.get("id") or ""
    ).strip() or None

    # Optional: category
    category = (row.get("category") or "").strip() or None

    if errors:
        return None, errors

    return StatementRecord(
        transaction_date=transaction_date,  # type: ignore[arg-type]
        description=description,
        amount=amount,  # type: ignore[arg-type]
        reference_id=reference_id,
        category=category,
    ), []


def ingest_csv(user_id: str, csv_content: str) -> IngestResult:
    """
    Parse and ingest a CSV file containing finance statement records.

    Args:
        user_id: The ID of the user uploading the statement.
        csv_content: The raw CSV content as a string.

    Returns:
        IngestResult containing counts and any errors encountered.
    """
    ingest_id = uuid4()
    timestamp = datetime.now(timezone.utc)
    records: list[StatementRecord] = []
    all_errors: list[IngestError] = []
    total_rows = 0

    try:
        reader = csv.DictReader(io.StringIO(csv_content))
        for row_number, row in enumerate(
            reader, start=2
        ):  # Start at 2 (header is row 1)
            total_rows += 1
            record, row_errors = parse_csv_row(row, row_number)
            if record:
                records.append(record)
            all_errors.extend(row_errors)
    except csv.Error as e:
        all_errors.append(
            IngestError(
                row_number=0,
                field=None,
                message=f"CSV parsing error: {e}",
            )
        )

    # Persist valid records
    success_count = 0
    if records:
        try:
            insert_statement_records(user_id, ingest_id, records)
            success_count = len(records)
        except Exception as e:
            all_errors.append(
                IngestError(
                    row_number=0,
                    field=None,
                    message=f"Database error: {e}",
                )
            )

    return IngestResult(
        ingest_id=ingest_id,
        timestamp=timestamp,
        total_records=total_rows,
        success_count=success_count,
        error_count=len(all_errors),
        errors=all_errors,
    )
