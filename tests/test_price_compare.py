"""Tests for price comparison utility."""
from drop_sentinel.helpers.price_compare import compare_prices, format_comparison
from drop_sentinel.models import Platform, Product, Variant


def _make_product(platform: Platform, title: str, price: float, currency: str, available: bool = True) -> Product:
    return Product(
        id=f"{platform.value}_{title}",
        platform=platform,
        title=title,
        url="https://example.com",
        variants=[Variant(id="1", title="Default", price=price, currency=currency, available=available)],
    )


def test_compare_sorts_by_usd_price():
    products = [
        _make_product(Platform.SHOPIFY_POPMART, "LABUBU", 12.99, "USD"),
        _make_product(Platform.LAZADA, "LABUBU", 299.0, "THB"),  # ~$8.37
        _make_product(Platform.SHOPEE, "LABUBU", 16.50, "SGD"),  # ~$12.21
    ]
    entries = compare_prices(products)
    assert len(entries) == 3
    assert entries[0].platform == "lazada"  # cheapest in USD
    assert entries[1].platform == "shopee"
    assert entries[2].platform == "shopify_popmart"


def test_out_of_stock_sorted_last():
    products = [
        _make_product(Platform.LAZADA, "LABUBU", 5.0, "USD", available=False),
        _make_product(Platform.SHOPEE, "LABUBU", 100.0, "USD", available=True),
    ]
    entries = compare_prices(products)
    assert entries[0].available is True
    assert entries[1].available is False


def test_zero_price_excluded():
    products = [
        _make_product(Platform.LAZADA, "Free Item", 0.0, "USD"),
        _make_product(Platform.SHOPEE, "Paid Item", 10.0, "USD"),
    ]
    entries = compare_prices(products)
    assert len(entries) == 1
    assert entries[0].price == 10.0


def test_format_comparison_empty():
    assert format_comparison([]) == "No prices to compare."


def test_format_comparison_has_content():
    products = [_make_product(Platform.SHOPIFY_POPMART, "LABUBU", 12.99, "USD")]
    entries = compare_prices(products)
    text = format_comparison(entries)
    assert "shopify_popmart" in text
    assert "12.99" in text
    assert "In Stock" in text
