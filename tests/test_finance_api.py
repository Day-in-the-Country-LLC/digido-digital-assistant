"""Integration tests for the finance ingest API endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from digido_digital_assistant.main import app

client = TestClient(app)


class TestFinanceIngestEndpoint:
    @patch("digido_digital_assistant.routes.ingest_csv")
    def test_ingest_success(self, mock_ingest):
        from datetime import datetime, timezone
        from uuid import uuid4

        from digido_digital_assistant.models import IngestResult

        mock_result = IngestResult(
            ingest_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            total_records=3,
            success_count=3,
            error_count=0,
            errors=[],
        )
        mock_ingest.return_value = mock_result

        response = client.post(
            "/v1/finance/ingest",
            json={
                "user_id": "test-user-123",
                "csv_content": "transaction_date,description,amount\n2024-01-15,Coffee,5.50\n",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] == 3
        assert data["success_count"] == 3
        assert data["error_count"] == 0
        assert "ingest_id" in data
        assert "timestamp" in data

    @patch("digido_digital_assistant.routes.ingest_csv")
    def test_ingest_partial_success(self, mock_ingest):
        from datetime import datetime, timezone
        from uuid import uuid4

        from digido_digital_assistant.models import IngestError, IngestResult

        mock_result = IngestResult(
            ingest_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            total_records=2,
            success_count=1,
            error_count=1,
            errors=[
                IngestError(
                    row_number=3, field="amount", message="Invalid amount format"
                ),
            ],
        )
        mock_ingest.return_value = mock_result

        response = client.post(
            "/v1/finance/ingest",
            json={
                "user_id": "test-user-123",
                "csv_content": "transaction_date,description,amount\n2024-01-15,Coffee,5.50\n2024-01-16,Tea,invalid\n",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["error_count"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["row_number"] == 3

    @patch("digido_digital_assistant.routes.ingest_csv")
    def test_ingest_all_failed(self, mock_ingest):
        from datetime import datetime, timezone
        from uuid import uuid4

        from digido_digital_assistant.models import IngestError, IngestResult

        mock_result = IngestResult(
            ingest_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            total_records=1,
            success_count=0,
            error_count=2,
            errors=[
                IngestError(
                    row_number=2, field="transaction_date", message="Invalid date"
                ),
                IngestError(row_number=2, field="amount", message="Invalid amount"),
            ],
        )
        mock_ingest.return_value = mock_result

        response = client.post(
            "/v1/finance/ingest",
            json={
                "user_id": "test-user-123",
                "csv_content": "transaction_date,description,amount\ninvalid,Test,abc\n",
            },
        )

        assert response.status_code == 400
        data = response.json()["detail"]
        assert data["message"] == "All records failed validation"
        assert data["success_count"] == 0
        assert data["error_count"] == 2

    def test_ingest_empty_csv(self):
        response = client.post(
            "/v1/finance/ingest",
            json={
                "user_id": "test-user-123",
                "csv_content": "",
            },
        )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_ingest_whitespace_only_csv(self):
        response = client.post(
            "/v1/finance/ingest",
            json={
                "user_id": "test-user-123",
                "csv_content": "   \n  \n  ",
            },
        )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_ingest_missing_user_id(self):
        response = client.post(
            "/v1/finance/ingest",
            json={
                "csv_content": "transaction_date,description,amount\n2024-01-15,Coffee,5.50\n",
            },
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_ingest_missing_csv_content(self):
        response = client.post(
            "/v1/finance/ingest",
            json={
                "user_id": "test-user-123",
            },
        )

        assert response.status_code == 422  # Pydantic validation error
