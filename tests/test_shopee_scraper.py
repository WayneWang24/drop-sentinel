"""Tests for Shopee scraper."""
from drop_sentinel.models import Platform
from drop_sentinel.scrapers.shopee import ShopeeScraper


def test_get_platform():
    scraper = ShopeeScraper()
    assert scraper.get_platform() == Platform.SHOPEE


def test_parse_item_valid():
    scraper = ShopeeScraper()
    item = {
        "itemid": 111222333,
        "shopid": 444555,
        "name": "Pop Mart SKULLPANDA",
        "price": 29900000,  # Shopee price in micro-cents
        "image": "abc123",
        "stock": 10,
    }
    product = scraper._parse_item(item, "th")
    assert product is not None
    assert product.id == "shopee_th_111222333"
    assert product.platform == Platform.SHOPEE
    assert product.title == "Pop Mart SKULLPANDA"
    assert product.variants[0].price == 299.0
    assert product.variants[0].currency == "THB"
    assert product.variants[0].available is True
    assert "shopee.co.th" in product.url


def test_parse_item_missing_fields():
    scraper = ShopeeScraper()
    item = {"price": 10000}
    product = scraper._parse_item(item, "sg")
    assert product is None


def test_parse_item_out_of_stock():
    scraper = ShopeeScraper()
    item = {
        "itemid": 999,
        "shopid": 888,
        "name": "Sold Out Item",
        "price": 5000000,
        "stock": 0,
    }
    product = scraper._parse_item(item, "my")
    assert product is not None
    assert product.variants[0].available is False


def test_parse_store_page_empty():
    scraper = ShopeeScraper()
    products = scraper._parse_store_page("<html></html>", "sg")
    assert products == []
