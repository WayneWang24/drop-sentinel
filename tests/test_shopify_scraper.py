"""Tests for Shopify scraper."""
import pytest
import httpx
from pytest_httpx import HTTPXMock

from drop_sentinel.scrapers.shopify import ShopifyScraper


MOCK_PRODUCTS_RESPONSE = {
    "products": [
        {
            "id": 12345,
            "title": "LABUBU The Monsters",
            "handle": "labubu-the-monsters",
            "tags": ["blind-box", "labubu"],
            "variants": [
                {
                    "id": 111,
                    "title": "Default",
                    "price": "12.99",
                    "available": True,
                    "sku": "PM-001",
                }
            ],
            "images": [{"src": "https://cdn.shopify.com/test.jpg"}],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-06-15T12:00:00Z",
        },
        {
            "id": 12346,
            "title": "DIMOO World",
            "handle": "dimoo-world",
            "tags": ["blind-box", "dimoo"],
            "variants": [
                {
                    "id": 222,
                    "title": "Default",
                    "price": "14.99",
                    "available": False,
                    "sku": "PM-002",
                }
            ],
            "images": [],
            "created_at": "2024-02-01T00:00:00Z",
            "updated_at": "2024-06-15T12:00:00Z",
        },
    ]
}


@pytest.mark.asyncio
async def test_fetch_products(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test.popmart.com/products.json?limit=250&page=1",
        json=MOCK_PRODUCTS_RESPONSE,
    )
    httpx_mock.add_response(
        url="https://test.popmart.com/products.json?limit=250&page=2",
        json={"products": []},
    )

    scraper = ShopifyScraper(
        base_url="https://test.popmart.com",
        store_name="test",
    )
    products = await scraper.fetch_products()

    assert len(products) == 2
    assert products[0].title == "LABUBU The Monsters"
    assert products[0].variants[0].price == 12.99
    assert products[0].variants[0].available is True
    assert products[1].title == "DIMOO World"
    assert products[1].variants[0].available is False


@pytest.mark.asyncio
async def test_check_product(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test.popmart.com/products/labubu-the-monsters.js",
        json=MOCK_PRODUCTS_RESPONSE["products"][0],
    )

    scraper = ShopifyScraper(
        base_url="https://test.popmart.com",
        store_name="test",
    )
    product = await scraper.check_product("labubu-the-monsters")

    assert product is not None
    assert product.title == "LABUBU The Monsters"
    assert product.available is True


@pytest.mark.asyncio
async def test_fetch_handles_http_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test.popmart.com/products.json?limit=250&page=1",
        status_code=403,
    )

    scraper = ShopifyScraper(
        base_url="https://test.popmart.com",
        store_name="test",
    )
    products = await scraper.fetch_products()
    assert len(products) == 0
