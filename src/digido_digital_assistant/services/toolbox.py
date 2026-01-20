from __future__ import annotations

from typing import Any, Protocol, TypedDict


class ToolResult(TypedDict):
    ok: bool
    data: dict[str, Any] | None
    error: str | None


class Toolbox(Protocol):
    def get_gmail_message(self, user_id: str, message_id: str) -> ToolResult: ...

    def mark_gmail_as_read(self, user_id: str, message_id: str) -> ToolResult: ...

    def modify_gmail_labels(
        self,
        user_id: str,
        message_id: str,
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> ToolResult: ...

    def create_gmail_draft(
        self,
        user_id: str,
        to: str,
        subject: str,
        body: str,
        cc: list[str] | None = None,
    ) -> ToolResult: ...

    def create_calendar_event(
        self,
        user_id: str,
        summary: str,
        start_time: str,
        end_time: str,
        timezone: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
        description: str | None = None,
        calendar_id: str = "primary",
    ) -> ToolResult: ...

    def create_drive_folder(
        self, user_id: str, folder_name: str, parent_id: str | None = None
    ) -> ToolResult: ...

    def upload_drive_file(
        self,
        user_id: str,
        file_path: str,
        file_name: str | None = None,
        parent_id: str | None = None,
        mime_type: str | None = None,
    ) -> ToolResult: ...

    def save_gmail_attachments_to_drive(
        self,
        user_id: str,
        message_id: str,
        attachment_ids: list[str],
        drive_folder_id: str | None = None,
    ) -> ToolResult: ...


class NullToolbox:
    def __init__(self, reason: str = "Toolbox not configured") -> None:
        self._reason = reason

    def _error(self) -> ToolResult:
        return {"ok": False, "data": None, "error": self._reason}

    def get_gmail_message(self, user_id: str, message_id: str) -> ToolResult:
        return self._error()

    def mark_gmail_as_read(self, user_id: str, message_id: str) -> ToolResult:
        return self._error()

    def modify_gmail_labels(
        self,
        user_id: str,
        message_id: str,
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> ToolResult:
        return self._error()

    def create_gmail_draft(
        self,
        user_id: str,
        to: str,
        subject: str,
        body: str,
        cc: list[str] | None = None,
    ) -> ToolResult:
        return self._error()

    def create_calendar_event(
        self,
        user_id: str,
        summary: str,
        start_time: str,
        end_time: str,
        timezone: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
        description: str | None = None,
        calendar_id: str = "primary",
    ) -> ToolResult:
        return self._error()

    def create_drive_folder(
        self, user_id: str, folder_name: str, parent_id: str | None = None
    ) -> ToolResult:
        return self._error()

    def upload_drive_file(
        self,
        user_id: str,
        file_path: str,
        file_name: str | None = None,
        parent_id: str | None = None,
        mime_type: str | None = None,
    ) -> ToolResult:
        return self._error()

    def save_gmail_attachments_to_drive(
        self,
        user_id: str,
        message_id: str,
        attachment_ids: list[str],
        drive_folder_id: str | None = None,
    ) -> ToolResult:
        return self._error()
