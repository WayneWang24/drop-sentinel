"""Damai (大麦) App automated ticket purchase.

Based on research of Damai app v9.0.19 (2026-04).
References:
  - RookieTree/DaMaiHelper (1779 stars, AccessibilityService)
  - WECENG/ticket-purchase (Appium implementation)
  - jiangbestone/damai_app_purchase

IMPORTANT: Use real devices, NOT emulators. Damai's anti-bot system
triggers continuous captcha on emulators.
"""
from __future__ import annotations

import logging
import time

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from drop_sentinel.auto.config import DamaiTarget
from drop_sentinel.auto.controller import DeviceSession

logger = logging.getLogger(__name__)

# Damai App identifiers
DAMAI_PACKAGE = "cn.damai"
DAMAI_ACTIVITY = "cn.damai.launcher.splash.SplashMainActivity"

# Known Activity classes in purchase flow
ACTIVITIES = {
    "detail": "cn.damai.trade.newtradeorder.ui.projectdetail.ui.activity.ProjectDetailActivity",
    "sku": "cn.damai.commonbusiness.seatbiz.sku.qilin.ui.NcovSkuActivity",
    "order": "cn.damai.ultron.view.activity.DmOrderActivity",
    "mine": "cn.damai.mine.activity.MineMainActivity",
}

# UI element selectors based on actual Damai app resource-ids
SELECTORS = {
    # 购买/状态栏按钮 (演出详情页底部)
    "buy_bar": (AppiumBy.ID, "cn.damai:id/trade_project_detail_purchase_status_bar_container_fl"),
    "buy_btn_text": (AppiumBy.ID, "cn.damai:id/tv_left_main_text"),
    "buy_btn_xpath": [
        (AppiumBy.XPATH, '//*[contains(@text,"立即购买")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"立即预订")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"选座购买")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"即刻抢购")]'),
        (AppiumBy.XPATH, '//*[@resource-id="cn.damai:id/tv_left_main_text"]'),
    ],
    # 票档选择 (新版票价text为空，需按index选)
    "ticket_tier_container": (AppiumBy.ID, "cn.damai:id/project_detail_perform_price_flowlayout"),
    "ticket_tier_items": (AppiumBy.XPATH,
        '//android.widget.FrameLayout[@resource-id="cn.damai:id/project_detail_perform_price_flowlayout"]'
        '//android.widget.FrameLayout[@clickable="true"]'),
    # 数量加号
    "quantity_plus": (AppiumBy.ID, "cn.damai:id/img_jia"),
    "quantity_layout": (AppiumBy.ID, "cn.damai:id/layout_num"),
    # SKU 确认购买
    "sku_buy_btn": [
        (AppiumBy.ID, "cn.damai:id/btn_buy"),
        (AppiumBy.ID, "cn.damai:id/btn_buy_view"),
    ],
    # 观演人 (订单页)
    "attendee_text": (AppiumBy.XPATH, '//android.widget.TextView[contains(@text,"")]'),
    # 确认/提交订单
    "confirm_btn": [
        (AppiumBy.XPATH, '//*[contains(@text,"立即提交")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"提交订单")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"确认")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"立即支付")]'),
    ],
    # 搜索
    "search_bar": (AppiumBy.ID, "cn.damai:id/search_bar"),
    "search_input": (AppiumBy.XPATH, '//android.widget.EditText'),
    "search_result_item": (AppiumBy.ID, "cn.damai:id/ll_search_item"),
    "search_result_title": (AppiumBy.ID, "cn.damai:id/item_title"),
    # 关闭弹窗
    "close_popup": [
        (AppiumBy.XPATH, '//*[contains(@resource-id,"close")]'),
        (AppiumBy.XPATH, '//*[contains(@content-desc,"关闭")]'),
        (AppiumBy.XPATH, '//*[contains(@resource-id,"iv_close")]'),
    ],
}

# Appium performance settings for speed
SPEED_SETTINGS = {
    "waitForIdleTimeout": 0,
    "actionAcknowledgmentTimeout": 0,
    "keyInjectionDelay": 0,
    "waitForSelectorTimeout": 300,
    "ignoreUnimportantViews": False,
    "allowInvisibleElements": True,
    "enableNotificationListener": False,
}


def optimize_session(session: DeviceSession) -> None:
    """Apply speed optimizations to an Appium session."""
    try:
        session.driver.update_settings(SPEED_SETTINGS)
        logger.info(f"Speed optimizations applied to {session.device.name}")
    except Exception as e:
        logger.warning(f"Failed to apply speed settings: {e}")


def purchase_ticket(session: DeviceSession, target: DamaiTarget) -> dict:
    """Execute ticket purchase flow on one device.

    Prerequisites:
        - Damai app is already open and logged in
        - User has already passed any verification/captcha
        - Recommended: already on the target show detail page

    Returns:
        dict with keys: success, message, device
    """
    driver = session.driver
    wait = WebDriverWait(driver, 10)
    result = {"success": False, "message": ""}

    optimize_session(session)

    try:
        # Step 1: Navigate to show (if not already there)
        if target.keyword and ACTIVITIES["detail"] not in (driver.current_activity or ""):
            _search_show(driver, wait, target.keyword)

        # Step 2: Dismiss any popups
        _dismiss_popups(driver)

        # Step 3: Click buy button on detail page
        bought = _click_buy_button(driver, max_retry=30, interval_ms=100)
        if not bought:
            result["message"] = "无法点击购买按钮（可能未开售或已售罄）"
            return result

        # Step 4: Select ticket tier on SKU page
        time.sleep(0.3)
        _select_ticket_tier(driver, target.ticket_tier)

        # Step 5: Adjust quantity
        _adjust_quantity(driver, target.num_tickets)

        # Step 6: Click confirm buy on SKU page
        _click_sku_buy(driver)

        # Step 7: Select attendees on order page
        time.sleep(0.5)
        if target.attendee_names:
            _select_attendees(driver, target.attendee_names)

        # Step 8: Submit order
        confirmed = _click_confirm(driver, wait)
        if confirmed:
            result["success"] = True
            result["message"] = "订单已提交，等待支付"
        else:
            result["message"] = "提交订单失败"

    except TimeoutException:
        result["message"] = "操作超时"
        logger.warning(f"Timeout on {session.device.name}")
    except Exception as e:
        result["message"] = f"异常: {e}"
        logger.error(f"Error on {session.device.name}: {e}")

    return result


def wait_and_buy(
    session: DeviceSession,
    target: DamaiTarget,
    sale_timestamp: float,
    pre_start_seconds: int = 3,
) -> dict:
    """Wait for sale time, then rapidly attempt purchase.

    Recommended flow:
        1. User opens Damai and navigates to the show detail page
        2. User passes any captcha/verification
        3. Call this function with the sale timestamp
        4. Script waits, then rapid-fires buy attempts at sale time

    Args:
        session: Active device session with Damai open on show page.
        target: Target show configuration.
        sale_timestamp: Unix timestamp of sale start.
        pre_start_seconds: Start clicking N seconds before sale time.
    """
    driver = session.driver
    result = {"success": False, "message": ""}

    optimize_session(session)

    # Wait until pre_start_seconds before sale
    now = time.time()
    wait_time = sale_timestamp - now - pre_start_seconds
    if wait_time > 0:
        logger.info(f"{session.device.name}: Waiting {wait_time:.0f}s...")
        time.sleep(wait_time)

    logger.info(f"{session.device.name}: Starting rapid buy attempts")

    # Phase 1: Rapid-click the buy button on detail page
    for attempt in range(100):
        try:
            # Try buy bar first (fastest, by ID)
            clicked = False
            for by, selector in SELECTORS["buy_btn_xpath"]:
                try:
                    btn = driver.find_element(by, selector)
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        clicked = True
                        logger.info(f"{session.device.name}: Buy clicked (attempt {attempt+1})")
                        break
                except NoSuchElementException:
                    continue

            if clicked:
                # Phase 2: SKU page - select tier + confirm
                time.sleep(0.2)
                _select_ticket_tier(driver, target.ticket_tier)
                _adjust_quantity(driver, target.num_tickets)
                _click_sku_buy(driver)

                # Phase 3: Order page - select attendees + submit
                time.sleep(0.3)
                if target.attendee_names:
                    _select_attendees(driver, target.attendee_names)
                if _click_confirm_fast(driver):
                    result["success"] = True
                    result["message"] = f"订单已提交 (attempt {attempt+1})"
                    return result

            time.sleep(0.05)  # 50ms between attempts

        except Exception as e:
            logger.debug(f"Attempt {attempt+1} error: {e}")
            continue

    result["message"] = "所有尝试均失败"
    return result


def _search_show(driver, wait, keyword: str) -> None:
    """Search for a show by keyword."""
    try:
        by, selector = SELECTORS["search_bar"]
        search = wait.until(EC.presence_of_element_located((by, selector)))
        search.click()
        time.sleep(0.5)

        by, selector = SELECTORS["search_input"]
        input_el = wait.until(EC.presence_of_element_located((by, selector)))
        input_el.send_keys(keyword)
        time.sleep(1)

        # Click first search result
        by, selector = SELECTORS["search_result_item"]
        items = driver.find_elements(by, selector)
        if items:
            items[0].click()
            time.sleep(2)
        else:
            # Fallback: find by text
            results = driver.find_elements(
                AppiumBy.XPATH,
                f'//android.widget.TextView[contains(@text,"{keyword[:6]}")]',
            )
            if results:
                results[0].click()
                time.sleep(2)
    except Exception as e:
        logger.warning(f"Search failed: {e}")


def _dismiss_popups(driver) -> None:
    """Try to close any popup dialogs."""
    for by, selector in SELECTORS["close_popup"]:
        try:
            el = driver.find_element(by, selector)
            el.click()
            time.sleep(0.2)
        except NoSuchElementException:
            pass


def _select_ticket_tier(driver, tier_index: int) -> None:
    """Select a ticket tier by index.

    Note: In recent Damai versions, ticket tier text is empty ("").
    Must locate by FrameLayout index within the price FlowLayout.
    """
    try:
        by, selector = SELECTORS["ticket_tier_items"]
        tiers = driver.find_elements(by, selector)
        if tiers and tier_index < len(tiers):
            tiers[tier_index].click()
            logger.debug(f"Selected ticket tier index {tier_index}")
            time.sleep(0.2)
        elif tiers:
            # Default to first available
            tiers[0].click()
            time.sleep(0.2)
    except Exception as e:
        logger.debug(f"Ticket tier selection: {e}")


def _adjust_quantity(driver, target_quantity: int) -> None:
    """Adjust ticket quantity using the plus button."""
    if target_quantity <= 1:
        return
    try:
        by, selector = SELECTORS["quantity_plus"]
        plus_btn = driver.find_element(by, selector)
        for _ in range(target_quantity - 1):
            plus_btn.click()
            time.sleep(0.05)
    except NoSuchElementException:
        logger.debug("Quantity plus button not found")


def _click_buy_button(driver, max_retry: int = 30, interval_ms: int = 100) -> bool:
    """Repeatedly try to click the buy button on detail page."""
    for _ in range(max_retry):
        for by, selector in SELECTORS["buy_btn_xpath"]:
            try:
                btn = driver.find_element(by, selector)
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    return True
            except NoSuchElementException:
                continue
        time.sleep(interval_ms / 1000)
    return False


def _click_sku_buy(driver) -> bool:
    """Click the buy/confirm button on SKU selection page."""
    for by, selector in SELECTORS["sku_buy_btn"]:
        try:
            btn = driver.find_element(by, selector)
            if btn.is_displayed():
                btn.click()
                return True
        except NoSuchElementException:
            continue
    return False


def _select_attendees(driver, names: list[str]) -> None:
    """Select attendees by name on the order page.

    Clicks on TextView elements whose text matches any of the
    provided attendee names.
    """
    try:
        for name in names:
            try:
                el = driver.find_element(
                    AppiumBy.XPATH,
                    f'//android.widget.TextView[contains(@text,"{name}")]',
                )
                el.click()
                time.sleep(0.1)
                logger.debug(f"Selected attendee: {name}")
            except NoSuchElementException:
                logger.warning(f"Attendee not found: {name}")
    except Exception as e:
        logger.debug(f"Attendee selection: {e}")


def _click_confirm(driver, wait) -> bool:
    """Click confirm/submit order button with wait."""
    for by, selector in SELECTORS["confirm_btn"]:
        try:
            btn = wait.until(EC.element_to_be_clickable((by, selector)))
            btn.click()
            return True
        except (NoSuchElementException, TimeoutException):
            continue
    return False


def _click_confirm_fast(driver) -> bool:
    """Quickly try to click confirm without waiting."""
    for by, selector in SELECTORS["confirm_btn"]:
        try:
            btn = driver.find_element(by, selector)
            if btn.is_displayed():
                btn.click()
                return True
        except NoSuchElementException:
            continue
    return False
