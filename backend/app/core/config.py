from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./data/platform.db"
    session_ttl_hours: int = 12
    cors_origins: str = "http://localhost:5173"
