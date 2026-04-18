"""Tests for Damai scraper."""
import pytest
from pytest_httpx import HTTPXMock

from drop_sentinel.scrapers.damai import DamaiScraper


MOCK_TOP_RESPONSE = {
    "alibaba_damai_ec_search_project_search_response": {
        "model": {
            "project_list": [
                {
                    "project_id": "777001",
                    "name": "周杰伦2026世界巡回演唱会-上海站",
                    "city_name": "上海",
                    "venue_name": "上海体育场",
                    "price_str": "380-1680元",
                    "promotion_price": "380",
                    "site_status": 3,
                    "show_time": "2026-08-15",
                    "vertical_pic": "https://img.damai.cn/test.jpg",
                },
                {
                    "project_id": "777002",
                    "name": "五月天演唱会",
                    "city_name": "北京",
                    "venue_name": "鸟巢",
                    "price_str": "280-1280元",
                    "promotion_price": "280",
                    "site_status": 4,  # 已售罄
                    "show_time": "2026-09-20",
                },
            ]
        }
    }
}


@pytest.mark.asyncio
async def test_fetch_with_top_api(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json=MOCK_TOP_RESPONSE)

    scraper = DamaiScraper(
        cities=["上海"],
        app_key="test_key",
        app_secret="test_secret",
    )
    products = await scraper.fetch_products()

    assert len(products) == 2
    assert products[0].title == "周杰伦2026世界巡回演唱会-上海站"
    assert products[0].variants[0].currency == "CNY"
    assert products[0].variants[0].available is True  # status 3 = 售票中
    assert products[1].variants[0].available is False  # status 4 = 已售罄


@pytest.mark.asyncio
async def test_fetch_without_api_key():
    scraper = DamaiScraper(cities=["上海"])  # No app_key
    products = await scraper.fetch_products()
    assert len(products) == 0  # Returns empty without credentials


@pytest.mark.asyncio
async def test_deduplication(httpx_mock: HTTPXMock):
    # Two cities returning overlapping results
    httpx_mock.add_response(json=MOCK_TOP_RESPONSE)
    httpx_mock.add_response(json=MOCK_TOP_RESPONSE)

    scraper = DamaiScraper(
        cities=["上海", "北京"],
        app_key="test_key",
        app_secret="test_secret",
    )
    products = await scraper.fetch_products()
    # Should deduplicate by ID
    assert len(products) == 2


def test_sign_top_request():
    scraper = DamaiScraper(app_key="test", app_secret="secret123")
    params = {"method": "test.api", "app_key": "test", "v": "1.0"}
    signature = scraper._sign_top_request(params)
    assert isinstance(signature, str)
    assert len(signature) == 32  # MD5 hex digest
    assert signature == signature.upper()  # Should be uppercase
