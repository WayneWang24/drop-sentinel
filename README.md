# Drop Sentinel

Release monitoring and purchase assistant for **Damai** (大麦网) tickets and **Pop Mart** (泡泡玛特) collectibles.

> **Legal & ethical**: This tool only monitors publicly available information and sends notifications. It does NOT automate purchases, bypass CAPTCHAs, or reverse-engineer APIs.

## Features

- **Multi-platform monitoring**: Pop Mart international (Shopify), Damai (大麦网), Lazada (TH/SG/MY/PH), Shopee (TH/SG/MY)
- **Social media tracking**: Weibo/小红书 RSS feeds for release announcements
- **Real-time notifications**: Telegram, Bark (iOS), Email, Webhook (Discord/Slack)
- **Stock change detection**: Restock alerts, new product discovery, price changes, out-of-stock
- **Cross-platform price comparison**: Normalized USD pricing across all channels
- **Deep link generation**: Quick-access links for each platform's app and web
- **Release calendar**: iCal subscription + HTML calendar with countdown timers
- **GitHub Pages dashboard**: Live dashboard with product cards, event log, and stats
- **Dual-mode operation**: GitHub Actions (free, every 15 min) or local daemon (30-second rush mode)

## Quick Start

```bash
# Clone
git clone https://github.com/WayneWang24/drop-sentinel.git
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
| `drop-sentinel monitor` | Run a single monitoring cycle |
| `drop-sentinel watch` | Start continuous monitoring daemon |
| `drop-sentinel watch --rush` | Rush mode (30-second intervals) |
| `drop-sentinel status` | Show current snapshot status |
| `drop-sentinel compare [KEYWORD]` | Cross-platform price comparison |
| `drop-sentinel deeplink URL` | Generate platform deep links |
| `drop-sentinel calendar` | Generate release calendar (iCal + HTML) |
| `drop-sentinel dashboard` | Generate static HTML dashboard |
| `drop-sentinel notify-test` | Send a test notification |

## Project Structure

```
src/drop_sentinel/
├── cli.py              # CLI entry point (9 commands)
├── config.py           # YAML + env var configuration
├── models.py           # Pydantic v2 data models
├── scrapers/
│   ├── base.py         # Base scraper interface
│   ├── shopify.py      # Pop Mart international (Shopify /products.json)
│   ├── damai.py        # 大麦网 (Alibaba TOP API)
│   ├── lazada.py       # Lazada TH/SG/MY/PH
│   ├── shopee.py       # Shopee TH/SG/MY
│   └── social.py       # Social media RSS (Weibo/小红书)
├── notifiers/
│   ├── base.py         # Base notifier interface
│   ├── telegram.py     # Telegram Bot API
│   ├── bark.py         # Bark iOS push
│   ├── email.py        # SMTP email
│   └── webhook.py      # Generic webhook (Discord/Slack)
├── store/
│   ├── json_store.py   # JSON snapshot storage
│   └── diff.py         # Change detection engine
├── generators/
│   ├── calendar.py     # iCal + HTML release calendar
│   ├── dashboard.py    # GitHub Pages dashboard
│   └── templates/      # Jinja2 HTML templates
└── helpers/
    ├── rate_limiter.py # Token bucket rate limiting
    ├── price_compare.py# Cross-platform price comparison
    └── deeplink.py     # Platform deep link generator
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
