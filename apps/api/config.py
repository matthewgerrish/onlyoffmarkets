"""
OnlyOffMarkets API settings.

Slim subset of the buyer-site config — only what off-market scrapers
and the public read API need. Everything is overridable via .env.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Persistence
    offmarket_db_url: str = ""  # empty → fall back to local SQLite

    # ATTOM Data — commercial off-market feed
    attom_api_key:  str = ""
    attom_base_url: str = "https://api.gateway.attomdata.com"
    attom_daily_cap: int = 2000

    # InvestorLift — wholesaler API (paid)
    investorlift_api_key:    str = ""
    investorlift_base_url:   str = "https://api.investorlift.com/v1"
    investorlift_market_filter: str = ""  # comma-separated postal codes / counties

    # Cache
    redis_url: str = "redis://localhost:6379/0"

    # CORS — Vite dev server + future prod domain
    allowed_origins: str = "http://localhost:5174,http://localhost:5173"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
