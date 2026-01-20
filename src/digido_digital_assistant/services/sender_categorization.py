from __future__ import annotations

import hashlib
import hmac
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from google.cloud import storage

from digido_digital_assistant.config import settings


@dataclass
class SenderCategoryEvent:
    sender_email: str
    sender_domain: str
    category: str
    user_id_hash: str
    timestamp: datetime
    source: str = "user"


@dataclass
class FlushResult:
    ok: bool
    count: int
    gcs_path: str | None
    error: str | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_user_id(user_id: str, secret: str) -> str:
    if not secret:
        return ""
    digest = hmac.new(secret.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest


def _parse_domain(sender_email: str) -> str:
    if "@" not in sender_email:
        return ""
    return sender_email.split("@", 1)[-1].strip().lower()


def _build_gcs_path(prefix: str, run_id: str, timestamp: datetime) -> str:
    date_part = timestamp.strftime("%Y-%m-%d")
    file_name = f"sender_labels_{run_id}.parquet"
    return f"{prefix}/ingest_date={date_part}/run_id={run_id}/{file_name}"


@dataclass
class SenderCategorizationBuffer:
    bucket_name: str = field(default_factory=lambda: settings.sender_categorization_bucket)
    prefix: str = field(default_factory=lambda: settings.sender_categorization_prefix)
    user_hash_secret: str = field(default_factory=lambda: settings.sender_categorization_user_hash_secret)
    events: list[SenderCategoryEvent] = field(default_factory=list)

    def record(
        self,
        user_id: str,
        sender_email: str,
        sender_domain: str | None,
        category: str,
        source: str = "user",
    ) -> None:
        domain = sender_domain or _parse_domain(sender_email)
        event = SenderCategoryEvent(
            sender_email=sender_email,
            sender_domain=domain,
            category=category,
            user_id_hash=_hash_user_id(user_id, self.user_hash_secret),
            timestamp=_utc_now(),
            source=source,
        )
        self.events.append(event)

    def flush_to_gcs(self) -> FlushResult:
        if not self.events:
            return FlushResult(ok=True, count=0, gcs_path=None)
        if not self.bucket_name:
            return FlushResult(ok=False, count=len(self.events), gcs_path=None, error="GCS bucket not configured.")

        run_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        gcs_path = _build_gcs_path(self.prefix, run_id, now)

        table = pa.Table.from_pylist([event.__dict__ for event in self.events])
        buffer = pa.BufferOutputStream()
        pq.write_table(table, buffer)
        data = buffer.getvalue()

        try:
            client = storage.Client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(gcs_path)
            blob.upload_from_string(data.to_pybytes(), content_type="application/octet-stream")
        except Exception as exc:
            return FlushResult(
                ok=False,
                count=len(self.events),
                gcs_path=gcs_path,
                error=str(exc),
            )

        count = len(self.events)
        self.events.clear()
        return FlushResult(ok=True, count=count, gcs_path=gcs_path)

    def snapshot(self) -> list[dict[str, Any]]:
        return [event.__dict__.copy() for event in self.events]
