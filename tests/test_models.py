"""Tests for data models."""
from drop_sentinel.models import (
    Event,
    EventType,
    Platform,
    Product,
    Snapshot,
    Variant,
)


def test_variant_creation():
    v = Variant(id="1", title="Default", price=9.99, available=True)
    assert v.available is True
    assert v.price == 9.99


def test_product_available_property():
    p = Product(
        id="1",
        platform=Platform.POPMART,
        title="Test",
        url="https://example.com",
        variants=[
            Variant(id="1", title="A", price=10.0, available=False),
            Variant(id="2", title="B", price=12.0, available=True),
        ],
    )
    assert p.available is True
    assert p.min_price == 12.0


def test_product_unavailable():
    p = Product(
        id="1",
        platform=Platform.POPMART,
        title="Test",
        url="https://example.com",
        variants=[
            Variant(id="1", title="A", price=10.0, available=False),
        ],
    )
    assert p.available is False
    assert p.min_price is None


def test_product_no_variants():
    p = Product(
        id="1",
        platform=Platform.POPMART,
        title="Test",
        url="https://example.com",
    )
    assert p.available is False
    assert p.min_price is None


def test_snapshot_serialization():
    s = Snapshot(
        platform=Platform.POPMART,
        products=[
            Product(
                id="1",
                platform=Platform.POPMART,
                title="Test",
                url="https://example.com",
            ),
        ],
    )
    json_str = s.model_dump_json()
    loaded = Snapshot.model_validate_json(json_str)
    assert loaded.platform == Platform.POPMART
    assert len(loaded.products) == 1


def test_event_creation():
    p = Product(
        id="1",
        platform=Platform.POPMART,
        title="Test",
        url="https://example.com",
    )
    e = Event(type=EventType.RESTOCK, product=p, details="Back in stock")
    assert e.type == EventType.RESTOCK
    assert e.details == "Back in stock"
