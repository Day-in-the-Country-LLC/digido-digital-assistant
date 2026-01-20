from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID


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


@dataclass(frozen=True)
class StatementRecord:
    """A single parsed record from a finance statement CSV."""

    transaction_date: date
    description: str
    amount: Decimal
    reference_id: str | None = None
    category: str | None = None


@dataclass(frozen=True)
class IngestError:
    """An error encountered during CSV ingestion."""

    row_number: int
    field: str | None
    message: str


@dataclass
class IngestResult:
    """Result of a finance statement ingestion operation."""

    ingest_id: UUID
    timestamp: datetime
    total_records: int
    success_count: int
    error_count: int
    errors: list[IngestError] = field(default_factory=list)
