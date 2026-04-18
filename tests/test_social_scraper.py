"""Tests for social media scraper."""
import pytest
from pytest_httpx import HTTPXMock

from drop_sentinel.scrapers.social import SocialScraper

MOCK_RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>泡泡玛特新品发售：LABUBU限定款</title>
      <link>https://weibo.com/test/1</link>
      <description>全新限定款LABUBU即将发售！&lt;img src="https://img.test.com/labubu.jpg"/&gt;</description>
      <pubDate>Fri, 18 Apr 2026 10:00:00 +0800</pubDate>
    </item>
    <item>
      <title>今天天气真好</title>
      <link>https://weibo.com/test/2</link>
      <description>无关内容</description>
      <pubDate>Fri, 18 Apr 2026 09:00:00 +0800</pubDate>
    </item>
    <item>
      <title>大麦网开票通知：周杰伦演唱会预售</title>
      <link>https://weibo.com/test/3</link>
      <description>开票啦！</description>
      <pubDate>Thu, 17 Apr 2026 12:00:00 +0800</pubDate>
    </item>
  </channel>
</rss>"""


@pytest.mark.asyncio
async def test_fetch_and_filter_by_keywords(httpx_mock: HTTPXMock):
    httpx_mock.add_response(text=MOCK_RSS_FEED)

    scraper = SocialScraper(
        feeds=[{
            "name": "test_feed",
            "url": "https://rsshub.test/feed",
            "type": "rss",
            "keywords": ["发售", "新品", "开票", "预售"],
        }],
    )
    products = await scraper.fetch_products()

    # "今天天气真好" should be filtered out (no matching keywords)
    assert len(products) == 2
    assert "LABUBU" in products[0].title
    assert "周杰伦" in products[1].title


@pytest.mark.asyncio
async def test_image_extraction(httpx_mock: HTTPXMock):
    httpx_mock.add_response(text=MOCK_RSS_FEED)

    scraper = SocialScraper(
        feeds=[{
            "name": "test",
            "url": "https://rsshub.test/feed",
            "type": "rss",
            "keywords": ["发售"],
        }],
    )
    releases = await scraper.fetch_releases()

    assert len(releases) >= 1
    assert releases[0].image_url == "https://img.test.com/labubu.jpg"


@pytest.mark.asyncio
async def test_handles_invalid_rss(httpx_mock: HTTPXMock):
    httpx_mock.add_response(text="<not valid xml>broken</")

    scraper = SocialScraper(
        feeds=[{
            "name": "broken",
            "url": "https://rsshub.test/broken",
            "type": "rss",
            "keywords": [],
        }],
    )
    products = await scraper.fetch_products()
    assert len(products) == 0  # Should handle gracefully


@pytest.mark.asyncio
async def test_handles_http_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=503)

    scraper = SocialScraper(
        feeds=[{
            "name": "down",
            "url": "https://rsshub.test/down",
            "type": "rss",
            "keywords": [],
        }],
    )
    products = await scraper.fetch_products()
    assert len(products) == 0
