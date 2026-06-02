from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    database_url: str = Field("postgresql+asyncpg://user:password@db:5432/memory_book", alias="DATABASE_URL")
    redis_url: str = Field("redis://redis:6379/0", alias="REDIS_URL")
    llm_provider: str = Field("gigachat", alias="LLM_PROVIDER")
    groq_api_key: str | None = Field(None, alias="GROQ_API_KEY")
    gigachat_auth_key: str | None = Field(None, alias="GIGACHAT_AUTH_KEY")
    whisper_model: str = Field("base", alias="WHISPER_MODEL")
    app_env: str = Field("development", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
