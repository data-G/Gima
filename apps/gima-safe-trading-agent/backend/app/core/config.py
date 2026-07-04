from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic import model_validator
from pydantic import AliasChoices
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gima Safe Trading Agent"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://gima:gima@localhost:5432/gima_safe_trading"

    trading_mode: str = Field(default="paper", pattern="^(paper|live)$")
    real_trading_enabled: bool = False
    live_trading_enabled: bool = Field(default=False, validation_alias=AliasChoices("LIVE_TRADING_ENABLED", "live_trading_enabled"))
    require_human_approval: bool = True
    broker_backend: str = Field(default="mock", pattern="^mock$")

    account_equity: float = 100_000.0
    max_risk_per_trade: float = 0.005
    max_daily_loss: float = 0.02
    max_weekly_loss: float = 0.05
    max_position_concentration: float = 0.10
    max_volatility: float = 0.06
    min_confidence: float = 0.60
    stale_data_seconds: int = 300
    create_tables_on_startup: bool = False

    notifications_enabled: bool = False
    whatsapp_mode: str = Field(default="mock", pattern="^(mock|cloud)$")
    whatsapp_graph_version: str = "v23.0"
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: SecretStr | None = None
    whatsapp_default_recipient: str = ""
    whatsapp_webhook_verify_token: SecretStr | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def enforce_v1_safety(self) -> "Settings":
        if self.broker_backend != "mock":
            raise ValueError("Only BROKER_BACKEND=mock is supported in this local paper-trading milestone.")
        if self.trading_mode == "live":
            raise ValueError("TRADING_MODE=live is disabled in v1. Use paper mode.")
        if not self.require_human_approval:
            raise ValueError("REQUIRE_HUMAN_APPROVAL=false is not allowed in v1.")
        if self.whatsapp_mode == "cloud" and self.notifications_enabled:
            if not self.whatsapp_phone_number_id or not self.whatsapp_access_token or not self.whatsapp_default_recipient:
                raise ValueError("WhatsApp Cloud notifications require phone number ID, access token, and default recipient.")
        return self

    @property
    def is_live_trading_allowed(self) -> bool:
        return self.trading_mode == "live" and (self.live_trading_enabled or self.real_trading_enabled)


@lru_cache
def get_settings() -> Settings:
    return Settings()
