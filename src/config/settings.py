from sqlalchemy.engine import URL
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    debug: bool = False
    title: str = "FastAPI Application"
    description: str = "A production-ready FastAPI application."
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000

    # Comma-separated origins allowed for CORS, e.g. "http://localhost:3000"
    cors_origins: str = ""

    # ------------------------------------------------------------------
    # Security / JWT
    # ------------------------------------------------------------------
    # Generate a strong key with: python -c "import secrets; print(secrets.token_hex(32))"
    secret_key: str = _DEFAULT_SECRET
    access_token_expire_minutes: int = 30

    @model_validator(mode="after")
    def _guard_secret_key(self) -> "Settings":
        if not self.debug and self.secret_key == _DEFAULT_SECRET:
            raise ValueError(
                "SECRET_KEY must be set to a strong random value in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if self.debug and self.secret_key == _DEFAULT_SECRET:
            import warnings
            warnings.warn(
                "SECRET_KEY is still the default value. Set a real key before deploying.",
                stacklevel=2,
            )
        return self

    # ------------------------------------------------------------------
    # Database — connection
    # ------------------------------------------------------------------
    db_user: str
    db_password: str
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str

    # ------------------------------------------------------------------
    # Database — connection pool
    # ------------------------------------------------------------------
    # How many persistent connections to keep open per process.
    db_pool_size: int = 10
    # Extra connections allowed above pool_size under burst traffic.
    # Total max = pool_size + max_overflow = 30 by default.
    db_max_overflow: int = 20
    # Seconds to wait for a free connection before raising TimeoutError.
    db_pool_timeout: int = 30
    # Recycle connections older than this many seconds (prevents stale TCP).
    # Must be less than the DB server's wait_timeout / tcp_keepalive setting.
    db_pool_recycle: int = 1800
    # Emit a SELECT 1 before handing a pooled connection to the app.
    db_pool_pre_ping: bool = True

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS_ORIGINS string into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
