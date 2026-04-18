"""Tests for configuration management."""
import os
import tempfile
from pathlib import Path

import yaml

from drop_sentinel.config import load_config


def test_default_config():
    config = load_config()
    assert len(config.shopify_stores) == 3
    assert config.monitor.interval_seconds == 300
    assert config.monitor.max_requests_per_minute == 12


def test_load_from_yaml():
    data = {
        "monitor": {"interval_seconds": 60},
        "shopify_stores": [
            {"name": "test_store", "base_url": "https://test.com"},
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(data, f)
        path = f.name

    try:
        config = load_config(path)
        assert config.monitor.interval_seconds == 60
        assert len(config.shopify_stores) == 1
        assert config.shopify_stores[0].name == "test_store"
    finally:
        os.unlink(path)


def test_env_var_override(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token-123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")

    config = load_config()
    assert config.notifiers.telegram.enabled is True
    assert config.notifiers.telegram.bot_token == "test-token-123"
    assert config.notifiers.telegram.chat_id == "12345"


def test_missing_config_file():
    config = load_config("/nonexistent/path.yml")
    # Should fall back to defaults
    assert len(config.shopify_stores) == 3
