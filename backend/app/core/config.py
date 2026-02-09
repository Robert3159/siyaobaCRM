from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "CRM Backend"
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_minutes: int = 60 * 24

    class Config:
        env_file = ".env"


settings = Settings()

