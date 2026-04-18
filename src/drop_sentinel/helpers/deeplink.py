"""Deep link generator for quick purchase access."""
from __future__ import annotations

import logging
from urllib.parse import quote, urlencode

logger = logging.getLogger(__name__)


def generate_deeplinks(product_url: str, title: str = "") -> dict[str, str]:
    """Generate platform-specific deep links from a product URL.

    Returns a dict of {platform: deeplink_url}.
    """
    links: dict[str, str] = {}

    if not product_url:
        return links

    # Direct web link (always available)
    links["web"] = product_url

    # Shopify / Pop Mart quick-add (if it's a Shopify store)
    if "popmart.com" in product_url:
        links["popmart_web"] = product_url

    # WeChat share link (for sharing to WeChat contacts)
    encoded_url = quote(product_url, safe="")
    links["wechat_share"] = product_url  # WeChat opens URLs natively

    # Mobile browser intent (Android)
    links["android_browser"] = f"intent://{product_url.replace('https://', '')}#Intent;scheme=https;end"

    # iOS universal link (Safari will handle popmart.com links)
    if "popmart.com" in product_url or "damai.cn" in product_url:
        links["ios_safari"] = product_url

    # Damai app deep link
    if "damai.cn" in product_url:
        links["damai_app"] = product_url  # damai.cn URLs open in app if installed
        # Also generate search link
        if title:
            links["damai_search"] = f"https://search.damai.cn/search.htm?keyword={quote(title)}"

    # Lazada app deep link
    if "lazada" in product_url:
        links["lazada_app"] = product_url  # Lazada URLs open in app

    # Shopee app deep link
    if "shopee" in product_url:
        links["shopee_app"] = product_url  # Shopee URLs open in app

    return links


def format_deeplinks(links: dict[str, str]) -> str:
    """Format deep links as readable text."""
    if not links:
        return "No links available."

    label_map = {
        "web": "Web",
        "popmart_web": "Pop Mart Website",
        "wechat_share": "WeChat Share",
        "android_browser": "Android",
        "ios_safari": "iOS Safari",
        "damai_app": "Damai App",
        "damai_search": "Damai Search",
        "lazada_app": "Lazada App",
        "shopee_app": "Shopee App",
    }

    lines = []
    for key, url in links.items():
        label = label_map.get(key, key)
        lines.append(f"  {label}: {url}")
    return "\n".join(lines)
