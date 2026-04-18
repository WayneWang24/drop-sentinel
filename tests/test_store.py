"""Tests for JSON store."""
import tempfile
from pathlib import Path

from drop_sentinel.models import Platform, Product, Snapshot, Variant
from drop_sentinel.store.json_store import JsonStore


def test_save_and_load_snapshot():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = JsonStore(tmpdir)
        snapshot = Snapshot(
            platform=Platform.POPMART,
            products=[
                Product(
                    id="1",
                    platform=Platform.POPMART,
                    title="Test Product",
                    url="https://example.com",
                    variants=[Variant(id="v1", title="Default", price=9.99, available=True)],
                ),
            ],
        )

        store.save_snapshot(snapshot)
        loaded = store.load_snapshot(Platform.POPMART)

        assert loaded is not None
        assert len(loaded.products) == 1
        assert loaded.products[0].title == "Test Product"
        assert loaded.products[0].variants[0].price == 9.99


def test_load_nonexistent():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = JsonStore(tmpdir)
        result = store.load_snapshot(Platform.DAMAI)
        assert result is None
