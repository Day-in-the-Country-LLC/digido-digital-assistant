"""Unit tests for the finance ingest orchestrator."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from digido_digital_assistant.services.finance.ingest_orchestrator import (
    ingest_csv,
    parse_amount,
    parse_csv_row,
    parse_date,
)


class TestParseDate:
    def test_parse_date_iso_format(self):
        result, error = parse_date("2024-01-15", 1)
        assert result == date(2024, 1, 15)
        assert error is None

    def test_parse_date_us_format(self):
        result, error = parse_date("01/15/2024", 1)
        assert result == date(2024, 1, 15)
        assert error is None

    def test_parse_date_eu_format(self):
        result, error = parse_date("15/01/2024", 1)
        assert result == date(2024, 1, 15)
        assert error is None

    def test_parse_date_invalid(self):
        result, error = parse_date("not-a-date", 5)
        assert result is None
        assert error is not None
        assert error.row_number == 5
        assert error.field == "transaction_date"
        assert "Invalid date format" in error.message


class TestParseAmount:
    def test_parse_amount_simple(self):
        result, error = parse_amount("100.50", 1)
        assert result == Decimal("100.50")
        assert error is None

    def test_parse_amount_with_commas(self):
        result, error = parse_amount("1,234.56", 1)
        assert result == Decimal("1234.56")
        assert error is None

    def test_parse_amount_with_dollar_sign(self):
        result, error = parse_amount("$500.00", 1)
        assert result == Decimal("500.00")
        assert error is None

    def test_parse_amount_negative(self):
        result, error = parse_amount("-75.25", 1)
        assert result == Decimal("-75.25")
        assert error is None

    def test_parse_amount_invalid(self):
        result, error = parse_amount("abc", 3)
        assert result is None
        assert error is not None
        assert error.row_number == 3
        assert error.field == "amount"


class TestParseCsvRow:
    def test_parse_valid_row(self):
        row = {
            "transaction_date": "2024-01-15",
            "description": "Coffee shop",
            "amount": "5.50",
        }
        record, errors = parse_csv_row(row, 2)
        assert record is not None
        assert len(errors) == 0
        assert record.transaction_date == date(2024, 1, 15)
        assert record.description == "Coffee shop"
        assert record.amount == Decimal("5.50")

    def test_parse_row_with_optional_fields(self):
        row = {
            "transaction_date": "2024-01-15",
            "description": "Restaurant",
            "amount": "45.00",
            "reference_id": "REF123",
            "category": "Dining",
        }
        record, errors = parse_csv_row(row, 2)
        assert record is not None
        assert record.reference_id == "REF123"
        assert record.category == "Dining"

    def test_parse_row_with_alternate_column_names(self):
        row = {
            "date": "2024-01-15",
            "memo": "Grocery store",
            "amount": "125.00",
            "ref": "TXN456",
        }
        record, errors = parse_csv_row(row, 2)
        assert record is not None
        assert record.description == "Grocery store"
        assert record.reference_id == "TXN456"

    def test_parse_row_missing_required_fields(self):
        row = {"amount": "10.00"}
        record, errors = parse_csv_row(row, 3)
        assert record is None
        assert len(errors) == 2  # Missing date and description

    def test_parse_row_invalid_date(self):
        row = {
            "transaction_date": "invalid",
            "description": "Test",
            "amount": "10.00",
        }
        record, errors = parse_csv_row(row, 4)
        assert record is None
        assert len(errors) == 1
        assert errors[0].field == "transaction_date"


class TestIngestCsv:
    @patch(
        "digido_digital_assistant.services.finance.ingest_orchestrator.insert_statement_records"
    )
    def test_ingest_valid_csv(self, mock_insert):
        csv_content = """transaction_date,description,amount
2024-01-15,Coffee,5.50
2024-01-16,Groceries,75.00
"""
        result = ingest_csv("user-123", csv_content)

        assert result.total_records == 2
        assert result.success_count == 2
        assert result.error_count == 0
        assert len(result.errors) == 0
        mock_insert.assert_called_once()

    @patch(
        "digido_digital_assistant.services.finance.ingest_orchestrator.insert_statement_records"
    )
    def test_ingest_partial_success(self, mock_insert):
        csv_content = """transaction_date,description,amount
2024-01-15,Coffee,5.50
invalid-date,Groceries,75.00
"""
        result = ingest_csv("user-123", csv_content)

        assert result.total_records == 2
        assert result.success_count == 1
        assert result.error_count == 1
        assert result.errors[0].row_number == 3

    @patch(
        "digido_digital_assistant.services.finance.ingest_orchestrator.insert_statement_records"
    )
    def test_ingest_all_failed(self, mock_insert):
        csv_content = """transaction_date,description,amount
invalid,Test,abc
"""
        result = ingest_csv("user-123", csv_content)

        assert result.total_records == 1
        assert result.success_count == 0
        assert result.error_count >= 1
        mock_insert.assert_not_called()

    @patch(
        "digido_digital_assistant.services.finance.ingest_orchestrator.insert_statement_records"
    )
    def test_ingest_empty_csv(self, mock_insert):
        csv_content = """transaction_date,description,amount
"""
        result = ingest_csv("user-123", csv_content)

        assert result.total_records == 0
        assert result.success_count == 0
        assert result.error_count == 0
        mock_insert.assert_not_called()

    @patch(
        "digido_digital_assistant.services.finance.ingest_orchestrator.insert_statement_records"
    )
    def test_ingest_database_error(self, mock_insert):
        mock_insert.side_effect = Exception("Database connection failed")
        csv_content = """transaction_date,description,amount
2024-01-15,Coffee,5.50
"""
        result = ingest_csv("user-123", csv_content)

        assert result.total_records == 1
        assert result.success_count == 0
        assert result.error_count == 1
        assert "Database error" in result.errors[0].message
