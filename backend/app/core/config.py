from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8899, alias="APP_PORT")
    public_api_base_url: str | None = Field(default=None, alias="PUBLIC_API_BASE_URL")
    public_site_url: str | None = Field(default=None, alias="PUBLIC_SITE_URL")
    cors_allowed_origins_raw: str = Field(
        default="http://localhost:5188,http://127.0.0.1:5188",
        alias="CORS_ALLOWED_ORIGINS",
    )
    database_url: str = Field(
        default="postgresql+psycopg://sparkmarket:sparkmarket@postgres:5432/sparkmarket",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    queue_mode: str = Field(default="redis", alias="QUEUE_MODE")
    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_expire_minutes: int = Field(default=1440, alias="JWT_EXPIRE_MINUTES")
    platform_fee_percent: int = Field(default=10, alias="PLATFORM_FEE_PERCENT")
    evaluation_threshold: int = Field(default=28, alias="EVALUATION_THRESHOLD")
    evaluator_provider: str = Field(default="mock", alias="EVALUATOR_PROVIDER")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5-mini", alias="OPENAI_MODEL")
    payment_provider: str = Field(default="simulated", alias="PAYMENT_PROVIDER")
    default_currency: str = Field(default="USD", alias="DEFAULT_CURRENCY")
    max_submissions_per_hour: int = Field(default=5, alias="MAX_SUBMISSIONS_PER_HOUR")
    similarity_threshold: float = Field(default=0.88, alias="SIMILARITY_THRESHOLD")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_allowed_origins(self) -> list[str]:
        raw_value = self.cors_allowed_origins_raw.strip()
        if not raw_value:
            return []
        if raw_value == "*":
            return ["*"]
        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
