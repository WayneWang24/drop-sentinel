"""Static dashboard generator for GitHub Pages."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from drop_sentinel.models import EventType, Platform, Snapshot

logger = logging.getLogger(__name__)

BADGE_CLASS_MAP = {
    EventType.NEW_PRODUCT: "new",
    EventType.RESTOCK: "restock",
    EventType.OUT_OF_STOCK: "oos",
    EventType.PRICE_CHANGE: "price",
    EventType.NEW_RELEASE: "new",
}

TYPE_LABEL_MAP = {
    EventType.NEW_PRODUCT: "New",
    EventType.RESTOCK: "Restock",
    EventType.OUT_OF_STOCK: "Sold Out",
    EventType.PRICE_CHANGE: "Price Change",
    EventType.NEW_RELEASE: "New Release",
}


class DashboardGenerator:
    """Generate static HTML dashboard from snapshot data."""

    def __init__(self, data_dir: str | Path = "data", output_dir: str | Path = "docs"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        templates_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True,
        )

    def generate(self) -> None:
        """Generate the full dashboard."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        snapshots = self._load_all_snapshots()
        recent_events = self._load_recent_events()

        all_products = []
        for snapshot in snapshots:
            all_products.extend(snapshot.products)

        available_list = [p for p in all_products if p.available]
        available_list.sort(key=lambda p: p.updated_at or datetime.min, reverse=True)

        template = self.env.get_template("index.html")
        html = template.render(
            updated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
            total_products=len(all_products),
            available_products=len(available_list),
            platform_count=len(snapshots),
            recent_events_count=len(recent_events),
            recent_events=recent_events,
            available_list=available_list[:50],  # Limit to 50 for page size
        )

        output_path = self.output_dir / "index.html"
        output_path.write_text(html, encoding="utf-8")
        logger.info(f"Dashboard generated: {output_path}")

        # Also write a JSON API file
        api_dir = self.output_dir / "api"
        api_dir.mkdir(exist_ok=True)
        api_data = {
            "updated_at": datetime.now(UTC).isoformat(),
            "total_products": len(all_products),
            "available_products": len(available_list),
            "platforms": [s.platform.value for s in snapshots],
        }
        (api_dir / "latest.json").write_text(
            json.dumps(api_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_all_snapshots(self) -> list[Snapshot]:
        """Load all snapshot files."""
        snapshots = []
        snapshots_dir = self.data_dir / "snapshots"
        if not snapshots_dir.exists():
            return snapshots

        for path in snapshots_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                snapshots.append(Snapshot.model_validate(data))
            except Exception as e:
                logger.warning(f"Failed to load {path}: {e}")
        return snapshots

    def _load_recent_events(self) -> list[dict]:
        """Load recent events from history files."""
        from drop_sentinel.models import Event

        events = []
        history_dir = self.data_dir / "history"
        if not history_dir.exists():
            return events

        # Get the most recent history files
        history_files = sorted(history_dir.glob("*.jsonl"), reverse=True)[:7]

        for path in history_files:
            try:
                for line in path.read_text(encoding="utf-8").strip().split("\n"):
                    if line:
                        event = Event.model_validate_json(line)
                        events.append({
                            "type_label": TYPE_LABEL_MAP.get(event.type, event.type.value),
                            "badge_class": BADGE_CLASS_MAP.get(event.type, "new"),
                            "product": event.product,
                            "details": event.details,
                            "timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M"),
                        })
            except Exception as e:
                logger.warning(f"Failed to parse {path}: {e}")

        # Sort by timestamp descending, limit to 20
        events.sort(key=lambda e: e["timestamp"], reverse=True)
        return events[:20]
