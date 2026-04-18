"""Tests for diff engine."""
from drop_sentinel.models import (
    EventType,
    Platform,
    Product,
    Snapshot,
    Variant,
)
from drop_sentinel.store.diff import DiffEngine


def _make_product(id: str, title: str, available: bool, price: float = 10.0) -> Product:
    return Product(
        id=id,
        platform=Platform.POPMART,
        title=title,
        url=f"https://example.com/products/{id}",
        variants=[Variant(id="v1", title="Default", price=price, available=available)],
    )


def _make_snapshot(products: list[Product]) -> Snapshot:
    return Snapshot(platform=Platform.POPMART, products=products)


def test_first_run_new_products():
    diff = DiffEngine()
    new = _make_snapshot([_make_product("1", "Labubu", True)])
    events = diff.compare(None, new)
    assert len(events) == 1
    assert events[0].type == EventType.NEW_PRODUCT


def test_first_run_skips_unavailable():
    diff = DiffEngine()
    new = _make_snapshot([_make_product("1", "Labubu", False)])
    events = diff.compare(None, new)
    assert len(events) == 0


def test_restock_detected():
    diff = DiffEngine()
    old = _make_snapshot([_make_product("1", "Labubu", False)])
    new = _make_snapshot([_make_product("1", "Labubu", True)])
    events = diff.compare(old, new)
    assert len(events) == 1
    assert events[0].type == EventType.RESTOCK


def test_out_of_stock_detected():
    diff = DiffEngine()
    old = _make_snapshot([_make_product("1", "Labubu", True)])
    new = _make_snapshot([_make_product("1", "Labubu", False)])
    events = diff.compare(old, new)
    assert len(events) == 1
    assert events[0].type == EventType.OUT_OF_STOCK


def test_price_change_detected():
    diff = DiffEngine()
    old = _make_snapshot([_make_product("1", "Labubu", True, price=9.99)])
    new = _make_snapshot([_make_product("1", "Labubu", True, price=12.99)])
    events = diff.compare(old, new)
    assert any(e.type == EventType.PRICE_CHANGE for e in events)
    price_event = [e for e in events if e.type == EventType.PRICE_CHANGE][0]
    assert price_event.old_price == 9.99
    assert price_event.new_price == 12.99


def test_no_change_no_events():
    diff = DiffEngine()
    old = _make_snapshot([_make_product("1", "Labubu", True, price=9.99)])
    new = _make_snapshot([_make_product("1", "Labubu", True, price=9.99)])
    events = diff.compare(old, new)
    assert len(events) == 0


def test_new_product_in_existing_snapshot():
    diff = DiffEngine()
    old = _make_snapshot([_make_product("1", "Labubu", True)])
    new = _make_snapshot([
        _make_product("1", "Labubu", True),
        _make_product("2", "Dimoo", True),
    ])
    events = diff.compare(old, new)
    assert len(events) == 1
    assert events[0].type == EventType.NEW_PRODUCT
    assert events[0].product.title == "Dimoo"
