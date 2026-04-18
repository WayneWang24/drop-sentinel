"""Tests for deep link generator."""
from drop_sentinel.helpers.deeplink import format_deeplinks, generate_deeplinks


def test_web_link_always_present():
    links = generate_deeplinks("https://www.example.com/product/1")
    assert "web" in links
    assert links["web"] == "https://www.example.com/product/1"


def test_popmart_links():
    links = generate_deeplinks("https://www.popmart.com/products/labubu")
    assert "popmart_web" in links
    assert "ios_safari" in links


def test_damai_links():
    links = generate_deeplinks("https://www.damai.cn/event/123", title="周杰伦演唱会")
    assert "damai_app" in links
    assert "damai_search" in links
    assert "search.damai.cn" in links["damai_search"]


def test_lazada_links():
    links = generate_deeplinks("https://www.lazada.co.th/products/labubu-123.html")
    assert "lazada_app" in links


def test_shopee_links():
    links = generate_deeplinks("https://shopee.co.th/product/123/456")
    assert "shopee_app" in links


def test_empty_url():
    links = generate_deeplinks("")
    assert links == {}


def test_format_deeplinks():
    links = generate_deeplinks("https://www.popmart.com/products/labubu")
    text = format_deeplinks(links)
    assert "Web" in text
    assert "Pop Mart" in text


def test_format_deeplinks_empty():
    assert format_deeplinks({}) == "No links available."
