"""
Centralized, typed configuration for the ArXiv MCP Server.

Every setting the server reads from the environment (or a `.env` file) is
declared here, once, and validated eagerly at startup. Nothing else in the
codebase should call `os.getenv(...)` directly — import `get_settings()`
instead.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, sourced from the environment / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Networking
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="text", alias="LOG_FORMAT")  # "text" | "json"

    # Semantic Scholar
    semantic_scholar_api_key: str | None = Field(default=None, alias="SEMANTIC_SCHOLAR_API_KEY")

    # HTTP access control
    mcp_api_key: str | None = Field(default=None, alias="MCP_API_KEY")
    rate_limit_per_minute: int = Field(default=30, alias="RATE_LIMIT_PER_MINUTE")

    # CORS. Empty = no browser-based clients expected;
    # the deployment is server-to-server / desktop-app only
    allowed_origins: str | None = Field(default=None, alias="ALLOWED_ORIGINS")

    # Outbound HTTP behavior
    request_deadline_seconds: float = Field(default=20.0, alias="REQUEST_DEADLINE_SECONDS")

    # FastMCP startup polish
    show_server_banner: bool = Field(default=True, alias="FASTMCP_SHOW_SERVER_BANNER")
    check_for_updates: bool = Field(default=True, alias="FASTMCP_CHECK_FOR_UPDATES")

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed)}, got {v!r}")
        return upper

    @field_validator("log_format")
    @classmethod
    def _validate_log_format(cls, v: str) -> str:
        lower = v.lower()
        if lower not in {"text", "json"}:
            raise ValueError(f"LOG_FORMAT must be 'text' or 'json', got {v!r}")
        return lower

    @property
    def allowed_origins_list(self) -> list[str]:
        if not self.allowed_origins:
            return []
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def has_semantic_scholar_key(self) -> bool:
        return bool(self.semantic_scholar_api_key and self.semantic_scholar_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings singleton, constructed once and cached."""
    return Settings()
