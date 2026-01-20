from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    digido_env: str = "development"

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    job_trigger_token: str = ""

    google_oauth_client_ids: list[str] = []
    google_oauth_client_secret: str = ""
    google_oauth_token_url: str = "https://oauth2.googleapis.com/token"
    google_oauth_userinfo_url: str = "https://openidconnect.googleapis.com/v1/userinfo"

    sender_categorization_bucket: str = "sender-categorization"
    sender_categorization_prefix: str = "sender_labels"
    sender_categorization_user_hash_secret: str = ""
    sender_categorization_categories: list[str] = [
        "Personal",
        "Work",
        "Shopping",
        "Finance",
        "Travel",
        "Health",
        "Education",
        "Entertainment",
        "Newsletters",
        "Events",
        "Utilities",
        "Other",
    ]

    gcp_project_id: str = ""
    openai_api_key: str = ""
    openai_api_key_secret_name: str = "OPENAI_API_KEY"
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.2

    summary_batch_limit: int = 200
    summary_job_timeout_seconds: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("google_oauth_client_ids", mode="before")
    @classmethod
    def _split_client_ids(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if value is None:
            return []
        return list(value)

    @field_validator("sender_categorization_categories", mode="before")
    @classmethod
    def _split_categories(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if value is None:
            return []
        return list(value)


settings = Settings()
