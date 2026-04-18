"""Configuration management for drop-sentinel."""
from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel, Field
import yaml


class ShopifyStoreConfig(BaseModel):
    """Config for a Shopify-based store."""
    name: str
    base_url: str  # e.g. "https://www.popmart.com"
    enabled: bool = True


class DamaiConfig(BaseModel):
    """Config for Damai scraper."""
    enabled: bool = True
    cities: list[str] = Field(default_factory=lambda: ["上海", "北京", "广州", "深圳"])


class TelegramConfig(BaseModel):
    """Telegram notification config."""
    bot_token: str = ""
    chat_id: str = ""
    enabled: bool = False


class BarkConfig(BaseModel):
    """Bark iOS push config."""
    server_url: str = "https://api.day.app"
    device_key: str = ""
    enabled: bool = False


class EmailConfig(BaseModel):
    """Email notification config."""
    smtp_host: str = ""
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    to_addresses: list[str] = Field(default_factory=list)
    enabled: bool = False


class WebhookConfig(BaseModel):
    """Generic webhook config."""
    url: str = ""
    enabled: bool = False


class NotifierConfig(BaseModel):
    """All notification channels."""
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    bark: BarkConfig = Field(default_factory=BarkConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    webhook: WebhookConfig = Field(default_factory=WebhookConfig)


class MonitorConfig(BaseModel):
    """Monitor behavior config."""
    interval_seconds: int = 300  # 5 minutes default
    rush_interval_seconds: int = 30
    max_requests_per_minute: int = 12
    user_agent: str = "DropSentinel/0.1 (+https://github.com/drop-sentinel)"


class Config(BaseModel):
    """Root configuration."""
    shopify_stores: list[ShopifyStoreConfig] = Field(default_factory=lambda: [
        ShopifyStoreConfig(name="popmart_global", base_url="https://www.popmart.com"),
        ShopifyStoreConfig(name="popmart_sg", base_url="https://www.popmart.com/sg"),
        ShopifyStoreConfig(name="popmart_jp", base_url="https://www.popmart.com/jp"),
    ])
    damai: DamaiConfig = Field(default_factory=DamaiConfig)
    notifiers: NotifierConfig = Field(default_factory=NotifierConfig)
    monitor: MonitorConfig = Field(default_factory=MonitorConfig)
    data_dir: str = "data"


def load_config(config_path: str | Path | None = None) -> Config:
    """Load config from YAML file, with environment variable overrides."""
    data = {}

    # Load from YAML if exists
    if config_path:
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}

    config = Config(**data)

    # Override from environment variables
    if token := os.getenv("TELEGRAM_BOT_TOKEN"):
        config.notifiers.telegram.bot_token = token
        config.notifiers.telegram.enabled = True
    if chat_id := os.getenv("TELEGRAM_CHAT_ID"):
        config.notifiers.telegram.chat_id = chat_id
    if bark_key := os.getenv("BARK_DEVICE_KEY"):
        config.notifiers.bark.device_key = bark_key
        config.notifiers.bark.enabled = True
    if webhook_url := os.getenv("WEBHOOK_URL"):
        config.notifiers.webhook.url = webhook_url
        config.notifiers.webhook.enabled = True

    return config
