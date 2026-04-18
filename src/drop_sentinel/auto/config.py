"""Configuration for automated purchase module."""
from __future__ import annotations

from pydantic import BaseModel, Field


class DeviceConfig(BaseModel):
    """Configuration for a single Android device/emulator."""
    name: str                          # Friendly name, e.g. "emulator-1"
    udid: str                          # ADB device ID, e.g. "emulator-5554"
    appium_port: int = 4723            # Appium server port for this device
    system_port: int = 8200            # UiAutomator2 system port
    platform_version: str = "12"       # Android version
    proxy: str = ""                    # Optional HTTP proxy, e.g. "socks5://127.0.0.1:1080"


class DamaiTarget(BaseModel):
    """Target show/event to purchase on Damai."""
    show_url: str = ""                 # Damai show URL or deep link
    show_id: str = ""                  # Show ID (from URL)
    keyword: str = ""                  # Search keyword to find the show
    ticket_tier: int = 0               # Preferred ticket tier index (0=first/cheapest)
    num_tickets: int = 1               # Number of tickets per order
    attendee_names: list[str] = Field(default_factory=list)  # Names to select
    max_price: float = 0               # Max price per ticket (0=any)


class PopMartTarget(BaseModel):
    """Target product to purchase on Pop Mart WeChat mini-program."""
    product_name: str = ""             # Product name to search for
    product_id: str = ""               # Product ID if known
    action: str = "lottery"            # "lottery" (抽签) or "flash_sale" (定时抢购)


class AutoConfig(BaseModel):
    """Root configuration for the auto module."""
    devices: list[DeviceConfig] = Field(default_factory=list)
    damai_targets: list[DamaiTarget] = Field(default_factory=list)
    popmart_targets: list[PopMartTarget] = Field(default_factory=list)

    # Timing
    countdown_start_seconds: int = 60  # Start refreshing N seconds before sale
    click_interval_ms: int = 100       # Interval between retry clicks

    # Safety
    max_retry: int = 30                # Max purchase retries before giving up
    screenshot_on_error: bool = True   # Save screenshot when errors occur
    screenshot_dir: str = "data/screenshots"
