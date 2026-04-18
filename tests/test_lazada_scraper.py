"""Tests for Lazada scraper."""
from drop_sentinel.models import Platform
from drop_sentinel.scrapers.lazada import LazadaScraper


def test_get_platform():
    scraper = LazadaScraper()
    assert scraper.get_platform() == Platform.LAZADA


def test_parse_item_valid():
    scraper = LazadaScraper()
    item = {
        "itemId": "12345",
        "name": "LABUBU Blind Box",
        "price": "299.00",
        "image": "https://img.lazada.co.th/abc.jpg",
        "itemUrl": "/products/labubu-12345.html",
    }
    product = scraper._parse_item(item, "th")
    assert product is not None
    assert product.id == "lazada_th_12345"
    assert product.platform == Platform.LAZADA
    assert product.title == "LABUBU Blind Box"
    assert product.variants[0].price == 299.0
    assert product.variants[0].currency == "THB"
    assert "lazada.co.th" in product.url


def test_parse_item_missing_id():
    scraper = LazadaScraper()
    item = {"name": "LABUBU"}
    product = scraper._parse_item(item, "sg")
    assert product is None


def test_parse_item_alt_fields():
    scraper = LazadaScraper()
    item = {
        "nid": "67890",
        "title": "DIMOO Figure",
        "priceShow": "45.50",
        "img": "https://img.lazada.sg/dimoo.jpg",
        "productUrl": "https://www.lazada.sg/products/dimoo-67890.html",
    }
    product = scraper._parse_item(item, "sg")
    assert product is not None
    assert product.id == "lazada_sg_67890"
    assert product.variants[0].currency == "SGD"
    assert product.variants[0].price == 45.5


def test_parse_store_page_empty():
    scraper = LazadaScraper()
    products = scraper._parse_store_page("<html><body>No data</body></html>", "th")
    assert products == []
