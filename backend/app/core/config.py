from functools import lru_cache
from urllib.parse import urlparse

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
    trusted_hosts_raw: str = Field(default="", alias="TRUSTED_HOSTS")
    database_url: str = Field(
        default="postgresql+psycopg://offering4ai:offering4ai@postgres:5432/offering4ai",
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
    email_delivery_mode: str = Field(default="log", alias="EMAIL_DELIVERY_MODE")
    email_from_address: str = Field(
        default="no-reply@offering4ai.local",
        alias="EMAIL_FROM_ADDRESS",
    )
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(default=False, alias="SMTP_USE_SSL")
    email_verify_token_expire_minutes: int = Field(
        default=60,
        alias="EMAIL_VERIFY_TOKEN_EXPIRE_MINUTES",
    )
    password_reset_token_expire_minutes: int = Field(
        default=60,
        alias="PASSWORD_RESET_TOKEN_EXPIRE_MINUTES",
    )
    registration_enabled: bool = Field(default=True, alias="REGISTRATION_ENABLED")
    session_cookie_name: str = Field(default="offering4ai_session", alias="SESSION_COOKIE_NAME")
    csrf_cookie_name: str = Field(default="offering4ai_csrf", alias="CSRF_COOKIE_NAME")
    csrf_header_name: str = Field(default="X-CSRF-Token", alias="CSRF_HEADER_NAME")
    session_cookie_secure: bool = Field(default=False, alias="SESSION_COOKIE_SECURE")
    enforce_https: bool = Field(default=True, alias="ENFORCE_HTTPS")
    security_headers_enabled: bool = Field(default=True, alias="SECURITY_HEADERS_ENABLED")
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    auth_rate_limit_count: int = Field(default=12, alias="AUTH_RATE_LIMIT_COUNT")
    auth_rate_limit_window_seconds: int = Field(
        default=300,
        alias="AUTH_RATE_LIMIT_WINDOW_SECONDS",
    )
    write_rate_limit_count: int = Field(default=30, alias="WRITE_RATE_LIMIT_COUNT")
    write_rate_limit_window_seconds: int = Field(
        default=300,
        alias="WRITE_RATE_LIMIT_WINDOW_SECONDS",
    )
    public_feed_rate_limit_count: int = Field(
        default=120,
        alias="PUBLIC_FEED_RATE_LIMIT_COUNT",
    )
    public_feed_rate_limit_window_seconds: int = Field(
        default=60,
        alias="PUBLIC_FEED_RATE_LIMIT_WINDOW_SECONDS",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_allowed_origins(self) -> list[str]:
        raw_value = self.cors_allowed_origins_raw.strip()
        if not raw_value:
            return []
        if raw_value == "*":
            return ["*"]
        return [origin.strip() for origin in raw_value.split(",") if origin.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        raw_value = self.trusted_hosts_raw.strip()
        if raw_value:
            return [host.strip() for host in raw_value.split(",") if host.strip()]

        hosts = {"localhost", "127.0.0.1", "testserver"}
        for value in (self.public_site_url, self.public_api_base_url):
            if not value:
                continue
            parsed = urlparse(value)
            if parsed.hostname:
                hosts.add(parsed.hostname)
        return sorted(hosts)

    @property
    def cookie_secure(self) -> bool:
        return self.session_cookie_secure or self.app_env.lower() == "production"

    @property
    def https_redirect_enabled(self) -> bool:
        return self.enforce_https and self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
