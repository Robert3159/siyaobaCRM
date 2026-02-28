from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "CRM Backend"
    database_url: str = ""
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_minutes: int = 60 * 24

    # SMTP settings for email verification
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 587
    smtp_use_starttls: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # Cloudflare Turnstile secret key
    turnstile_secret_key: str = ""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
