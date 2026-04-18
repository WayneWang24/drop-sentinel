"""CLI entry point for drop-sentinel."""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from drop_sentinel.config import load_config
from drop_sentinel.models import Platform

app = typer.Typer(
    name="drop-sentinel",
    help="Release monitoring and purchase assistant for Damai & Pop Mart.",
)
console = Console()


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def _run_monitor(
    platform: str,
    config_path: str | None,
    verbose: bool,
) -> None:
    """Core monitor logic."""
    setup_logging(verbose)
    logger = logging.getLogger("drop_sentinel")

    config = load_config(config_path)

    from drop_sentinel.helpers.rate_limiter import RateLimiter
    from drop_sentinel.notifiers.telegram import TelegramNotifier
    from drop_sentinel.scrapers.shopify import ShopifyScraper
    from drop_sentinel.store.diff import DiffEngine
    from drop_sentinel.store.json_store import JsonStore

    store = JsonStore(config.data_dir)
    diff_engine = DiffEngine()
    rate_limiter = RateLimiter(config.monitor.max_requests_per_minute)

    # Build notifiers
    notifiers = []
    if config.notifiers.telegram.enabled:
        notifiers.append(TelegramNotifier(
            bot_token=config.notifiers.telegram.bot_token,
            chat_id=config.notifiers.telegram.chat_id,
        ))

    from drop_sentinel.scrapers.damai import DamaiScraper
    from drop_sentinel.scrapers.social import SocialScraper

    # Build scrapers based on platform filter
    scrapers = []
    if platform in ("all", "shopify"):
        for store_cfg in config.shopify_stores:
            if store_cfg.enabled:
                scrapers.append(ShopifyScraper(
                    base_url=store_cfg.base_url,
                    store_name=store_cfg.name,
                    user_agent=config.monitor.user_agent,
                    rate_limiter=rate_limiter,
                ))

    if platform in ("all", "damai") and config.damai.enabled:
        scrapers.append(DamaiScraper(
            cities=config.damai.cities,
            keywords=config.damai.keywords,
            app_key=config.damai.app_key,
            app_secret=config.damai.app_secret,
            user_agent=config.monitor.user_agent,
            rate_limiter=rate_limiter,
        ))

    if platform in ("all", "social") and config.social.enabled:
        scrapers.append(SocialScraper(
            feeds=config.social.feeds or None,
            user_agent=config.monitor.user_agent,
            rate_limiter=rate_limiter,
        ))

    if not scrapers:
        console.print("[yellow]No scrapers enabled for the selected platform.[/yellow]")
        return

    total_events = 0

    for scraper in scrapers:
        name = getattr(scraper, "store_name", scraper.get_platform().value)
        console.print(f"[blue]Scanning {name}...[/blue]")

        try:
            new_snapshot = await scraper.take_snapshot()
        except Exception as e:
            console.print(f"[red]Error scanning {name}: {e}[/red]")
            logger.exception(f"Scraper error: {name}")
            continue

        old_snapshot = store.load_snapshot(scraper.get_platform())
        events = diff_engine.compare(old_snapshot, new_snapshot)

        store.save_snapshot(new_snapshot)
        if events:
            store.append_history(scraper.get_platform(), events)

        console.print(
            f"  Products: {len(new_snapshot.products)}, "
            f"Events: {len(events)}"
        )

        # Send notifications
        for event in events:
            for notifier in notifiers:
                try:
                    await notifier.send(event)
                except Exception as e:
                    logger.error(f"Notification failed: {e}")

        total_events += len(events)

    console.print(f"\n[green]Done. Total events: {total_events}[/green]")


@app.command()
def monitor(
    platform: str = typer.Option("all", help="Platform: all, shopify, damai, social"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config.yml"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Run a single monitoring cycle across configured platforms."""
    asyncio.run(_run_monitor(platform, config_path, verbose))


@app.command()
def notify_test(
    channel: str = typer.Option("telegram", help="Channel to test: telegram"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c"),
) -> None:
    """Send a test notification to verify channel setup."""
    from drop_sentinel.models import Event, EventType, Product, Variant

    config = load_config(config_path)

    test_product = Product(
        id="test-001",
        platform=Platform.SHOPIFY_POPMART,
        title="Test Product - Drop Sentinel",
        url="https://www.popmart.com",
        variants=[Variant(id="1", title="Default", price=9.99, available=True)],
    )
    test_event = Event(
        type=EventType.RESTOCK,
        product=test_product,
        details="This is a test notification from Drop Sentinel.",
    )

    async def _send() -> None:
        if channel == "telegram":
            from drop_sentinel.notifiers.telegram import TelegramNotifier

            if not config.notifiers.telegram.enabled:
                console.print("[red]Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.[/red]")
                return
            notifier = TelegramNotifier(
                bot_token=config.notifiers.telegram.bot_token,
                chat_id=config.notifiers.telegram.chat_id,
            )
            ok = await notifier.send(test_event)
            if ok:
                console.print("[green]Test notification sent successfully![/green]")
            else:
                console.print("[red]Failed to send test notification.[/red]")
        else:
            console.print(f"[yellow]Unknown channel: {channel}[/yellow]")

    asyncio.run(_send())


@app.command()
def status(
    config_path: Optional[str] = typer.Option(None, "--config", "-c"),
) -> None:
    """Show current monitoring status and latest snapshots."""
    config = load_config(config_path)

    from drop_sentinel.store.json_store import JsonStore

    store = JsonStore(config.data_dir)
    table = Table(title="Drop Sentinel Status")
    table.add_column("Platform", style="cyan")
    table.add_column("Products", style="green")
    table.add_column("Available", style="yellow")
    table.add_column("Last Update", style="blue")

    for plat in Platform:
        snapshot = store.load_snapshot(plat)
        if snapshot:
            available = sum(1 for p in snapshot.products if p.available)
            table.add_row(
                plat.value,
                str(len(snapshot.products)),
                str(available),
                snapshot.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            )

    console.print(table)


@app.command()
def calendar(
    config_path: Optional[str] = typer.Option(None, "--config", "-c"),
    output_dir: str = typer.Option("docs", "--output", "-o", help="Output directory"),
) -> None:
    """Generate release calendar (iCal + HTML)."""
    config = load_config(config_path)

    from drop_sentinel.generators.calendar import CalendarGenerator

    gen = CalendarGenerator(data_dir=config.data_dir, output_dir=output_dir)
    gen.generate()
    console.print(f"[green]Calendar generated in {output_dir}/calendar/[/green]")


@app.command()
def dashboard(
    config_path: Optional[str] = typer.Option(None, "--config", "-c"),
    output_dir: str = typer.Option("docs", "--output", "-o", help="Output directory"),
) -> None:
    """Generate static HTML dashboard for GitHub Pages."""
    config = load_config(config_path)

    from drop_sentinel.generators.dashboard import DashboardGenerator

    gen = DashboardGenerator(data_dir=config.data_dir, output_dir=output_dir)
    gen.generate()
    console.print(f"[green]Dashboard generated in {output_dir}/[/green]")


if __name__ == "__main__":
    app()
