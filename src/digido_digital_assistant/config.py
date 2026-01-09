from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    digido_env: str = "development"

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    job_trigger_token: str = ""

    summary_batch_limit: int = 200
    summary_job_timeout_seconds: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
