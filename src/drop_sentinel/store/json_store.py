"""JSON file-based storage for snapshots and history."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from drop_sentinel.models import Platform, Snapshot

logger = logging.getLogger(__name__)


class JsonStore:
    """Store snapshots as JSON files for Git tracking."""

    def __init__(self, data_dir: str | Path = "data"):
        self.data_dir = Path(data_dir)
        self.snapshots_dir = self.data_dir / "snapshots"
        self.history_dir = self.data_dir / "history"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, snapshot: Snapshot) -> Path:
        """Save a snapshot, overwriting the latest for this platform."""
        filename = f"{snapshot.platform.value}.json"
        path = self.snapshots_dir / filename
        path.write_text(
            snapshot.model_dump_json(indent=2),
            encoding="utf-8",
        )
        logger.info(f"Saved snapshot: {path}")
        return path

    def load_snapshot(self, platform: Platform) -> Snapshot | None:
        """Load the latest snapshot for a platform."""
        filename = f"{platform.value}.json"
        path = self.snapshots_dir / filename
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Snapshot.model_validate(data)
        except Exception as e:
            logger.warning(f"Failed to load snapshot {path}: {e}")
            return None

    def append_history(self, platform: Platform, events: list) -> None:
        """Append events to the daily history log."""
        if not events:
            return
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        filename = f"{platform.value}_{today}.jsonl"
        path = self.history_dir / filename
        with open(path, "a", encoding="utf-8") as f:
            for event in events:
                f.write(event.model_dump_json() + "\n")
        logger.info(f"Appended {len(events)} events to {path}")
