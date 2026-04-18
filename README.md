# Drop Sentinel

Release monitoring and purchase assistant for **Damai** (大麦网) tickets and **Pop Mart** (泡泡玛特) collectibles.

> **Legal & ethical**: This tool only monitors publicly available information and sends notifications. It does NOT automate purchases, bypass CAPTCHAs, or reverse-engineer APIs.

## Features

- **Multi-platform monitoring**: Pop Mart international (Shopify), Damai, Lazada, Shopee
- **Real-time notifications**: Telegram, Bark (iOS), Email, Webhook
- **Stock change detection**: Restock alerts, new product discovery, price change tracking
- **GitHub Pages dashboard**: Live dashboard showing available products and recent events
- **Dual-mode operation**: GitHub Actions (free, every 15 min) or local daemon (30-second intervals)

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USER/drop-sentinel.git
cd drop-sentinel

# Install
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Configure
cp config/config.example.yml config/config.yml
# Edit config/config.yml with your notification settings

# Run once
drop-sentinel monitor

# Check status
drop-sentinel status

# Generate dashboard
drop-sentinel dashboard
```

## Notification Setup

### Telegram
1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Get your chat ID via [@userinfobot](https://t.me/userinfobot)
3. Set environment variables:
```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```

### Bark (iOS)
```bash
export BARK_DEVICE_KEY="your-device-key"
```

## GitHub Actions Setup

1. Fork this repo
2. Add secrets in Settings > Secrets:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Enable GitHub Actions
4. Enable GitHub Pages (Settings > Pages > Source: GitHub Actions)

The monitor runs every 15 minutes automatically.

## CLI Commands

| Command | Description |
|---------|-------------|
| `drop-sentinel monitor` | Run a monitoring cycle |
| `drop-sentinel status` | Show current snapshot status |
| `drop-sentinel dashboard` | Generate static HTML dashboard |
| `drop-sentinel notify-test` | Send a test notification |

## Project Structure

```
src/drop_sentinel/
├── cli.py              # CLI entry point
├── config.py           # Configuration management
├── models.py           # Data models
├── scrapers/           # Platform-specific scrapers
│   ├── base.py         # Base scraper interface
│   └── shopify.py      # Shopify (Pop Mart international)
├── notifiers/          # Notification channels
│   ├── base.py         # Base notifier interface
│   └── telegram.py     # Telegram bot
├── store/              # Data storage
│   ├── json_store.py   # JSON file store
│   └── diff.py         # Change detection engine
└── generators/         # Static site generation
    ├── dashboard.py    # Dashboard generator
    └── templates/      # HTML templates
```

## Legal Notice

This tool is for personal use and educational purposes only. It monitors publicly available information and does not:
- Bypass any security measures or CAPTCHAs
- Automate actual purchases or payments
- Reverse-engineer proprietary APIs
- Violate any platform's Terms of Service

Users are responsible for complying with all applicable laws and platform policies.

## License

MIT
