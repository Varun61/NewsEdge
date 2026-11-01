"""NewsEdge application configuration using Pydantic Settings."""

from enum import Enum
from pathlib import Path
from typing import Optional
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AIProvider(str, Enum):
    """Supported AI provider backends."""
    OLLAMA = "ollama"
    OPENAI = "openai"


class MarketDataProvider(str, Enum):
    """Supported market-data providers."""
    NONE = "none"


class Settings(BaseSettings):
    """Central application settings, loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Project paths ───────────────────────────────────────────────────
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)

    # ── AI provider ─────────────────────────────────────────────────────
    ai_provider: AIProvider = AIProvider.OLLAMA
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    # ── Telegram ────────────────────────────────────────────────────────
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_authorized_users: str = ""

    # ── Groww Integration ───────────────────────────────────────────────
    groww_auth_token: Optional[str] = None
    groww_email: Optional[str] = None
    groww_password: Optional[str] = None
    groww_totp_secret: Optional[str] = None

    # ── Database ────────────────────────────────────────────────────────
    database_url: str = "sqlite:///data/newsedge.db"

    # ── General ─────────────────────────────────────────────────────────
    log_level: str = "INFO"
    timezone: str = "Asia/Kolkata"

    # ── Collection window (IST hours) ───────────────────────────────────
    collection_start_hour: int = 15
    collection_start_minute: int = 30
    collection_end_hour: int = 7
    collection_end_minute: int = 59

    # ── Market data ─────────────────────────────────────────────────────
    market_data_provider: MarketDataProvider = MarketDataProvider.NONE

    # ── Scoring weights (must sum to 100) ───────────────────────────────
    weight_news_impact: float = 25.0
    weight_financial_materiality: float = 20.0
    weight_source_credibility: float = 15.0
    weight_freshness: float = 10.0
    weight_confirmations: float = 10.0
    weight_historical_reaction: float = 10.0
    weight_company_confidence: float = 10.0

    # ── Derived helpers ─────────────────────────────────────────────────
    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def reports_dir(self) -> Path:
        return self.project_root / "reports"

    @property
    def logs_dir(self) -> Path:
        return self.project_root / "logs"

    @property
    def authorized_user_ids(self) -> list[int]:
        if not self.telegram_authorized_users:
            return []
        ids = []
        for uid in self.telegram_authorized_users.split(","):
            u = uid.strip()
            if u.isdigit():
                ids.append(int(u))
        return ids

    def get_db_path(self) -> Path:
        """Return the resolved file-system path for an sqlite:/// URL."""
        if self.database_url.startswith("sqlite:///"):
            rel = self.database_url.replace("sqlite:///", "")
            return self.project_root / rel
        return Path(self.database_url)


@lru_cache()
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()
