"""Damai (大麦) App automated ticket purchase."""
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
DAMAI_ACTIVITY = "cn.damai.homepage.MainActivity"

# Common UI element patterns (may need updating as app changes)
# These are based on known Damai app UI structures
SELECTORS = {
    # 购买按钮 (multiple possible texts)
    "buy_btn": [
        (AppiumBy.XPATH, '//*[contains(@text,"立即购买")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"立即预订")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"选座购买")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"即刻抢购")]'),
    ],
    # 票档选择 (ticket tier)
    "ticket_tier": (AppiumBy.XPATH, '//android.widget.LinearLayout[contains(@resource-id,"sku")]'),
    # 场次选择 (performance/session)
    "performance": (AppiumBy.XPATH, '//android.widget.LinearLayout[contains(@resource-id,"perform")]'),
    # 数量加减
    "quantity_plus": (AppiumBy.XPATH, '//*[contains(@resource-id,"plus") or contains(@text,"+")]'),
    # 观演人选择
    "attendee_checkbox": (AppiumBy.XPATH, '//android.widget.CheckBox'),
    "attendee_name": (AppiumBy.XPATH, '//android.widget.TextView[contains(@resource-id,"viewer_name")]'),
    # 确认订单
    "confirm_btn": [
        (AppiumBy.XPATH, '//*[contains(@text,"确认")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"提交订单")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"立即支付")]'),
    ],
    # 搜索
    "search_box": (AppiumBy.XPATH, '//android.widget.EditText'),
    "search_btn": (AppiumBy.XPATH, '//*[contains(@text,"搜索")]'),
    # 关闭弹窗
    "close_popup": [
        (AppiumBy.XPATH, '//*[contains(@resource-id,"close")]'),
        (AppiumBy.XPATH, '//*[contains(@content-desc,"关闭")]'),
    ],
}


def purchase_ticket(session: DeviceSession, target: DamaiTarget) -> dict:
    """Execute ticket purchase flow on one device.

    Prerequisites:
        - Damai app is already open and logged in
        - User has already passed any verification/captcha
        - Target show page is already open (or keyword is provided)

    Returns:
        dict with keys: success, message, device
    """
    driver = session.driver
    wait = WebDriverWait(driver, 10)
    result = {"success": False, "message": ""}

    try:
        # Step 1: Navigate to show (if not already there)
        if target.keyword:
            _search_show(driver, wait, target.keyword)

        # Step 2: Dismiss any popups
        _dismiss_popups(driver)

        # Step 3: Select ticket tier
        if target.ticket_tier >= 0:
            _select_ticket_tier(driver, target.ticket_tier)

        # Step 4: Click buy button (with retry)
        bought = _click_buy_button(driver, wait, max_retry=30, interval_ms=100)
        if not bought:
            result["message"] = "无法点击购买按钮（可能未开售或已售罄）"
            return result

        # Step 5: Select attendees
        if target.attendee_names:
            _select_attendees(driver, wait, target.attendee_names)

        # Step 6: Confirm order
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

    This is the main entry point for timed purchases. Call this
    when the show page is already open and you want to buy at
    the exact sale time.

    Args:
        session: Active device session with Damai open on show page.
        target: Target show configuration.
        sale_timestamp: Unix timestamp of sale start.
        pre_start_seconds: Start clicking N seconds before sale time.
    """
    driver = session.driver
    result = {"success": False, "message": ""}

    # Wait until pre_start_seconds before sale
    now = time.time()
    wait_time = sale_timestamp - now - pre_start_seconds
    if wait_time > 0:
        logger.info(f"{session.device.name}: Waiting {wait_time:.0f}s...")
        time.sleep(wait_time)

    logger.info(f"{session.device.name}: Starting rapid buy attempts")

    # Rapid-fire buy attempts
    for attempt in range(target.num_tickets * 50):
        try:
            # Try to click any buy button
            for by, selector in SELECTORS["buy_btn"]:
                try:
                    btn = driver.find_element(by, selector)
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        logger.info(f"{session.device.name}: Buy button clicked (attempt {attempt+1})")

                        # After clicking buy, try to confirm order
                        time.sleep(0.3)
                        if _select_attendees_if_needed(driver, target.attendee_names):
                            time.sleep(0.2)
                        if _click_confirm_fast(driver):
                            result["success"] = True
                            result["message"] = f"订单已提交 (attempt {attempt+1})"
                            return result
                except NoSuchElementException:
                    continue

            time.sleep(0.1)  # Brief pause between attempts

        except Exception as e:
            logger.debug(f"Attempt {attempt+1} error: {e}")
            continue

    result["message"] = "所有尝试均失败"
    return result


def _search_show(driver, wait, keyword: str) -> None:
    """Search for a show by keyword."""
    try:
        search = wait.until(EC.presence_of_element_located(SELECTORS["search_box"]))
        search.click()
        search.send_keys(keyword)
        # Click search button
        for by, sel in [SELECTORS["search_btn"]]:
            try:
                driver.find_element(by, sel).click()
                break
            except NoSuchElementException:
                pass
        time.sleep(2)
        # Click first result
        results = driver.find_elements(AppiumBy.XPATH, '//android.widget.TextView[contains(@text,"' + keyword[:4] + '")]')
        if results:
            results[0].click()
            time.sleep(1)
    except Exception as e:
        logger.warning(f"Search failed: {e}")


def _dismiss_popups(driver) -> None:
    """Try to close any popup dialogs."""
    for by, selector in SELECTORS["close_popup"]:
        try:
            el = driver.find_element(by, selector)
            el.click()
            time.sleep(0.3)
        except NoSuchElementException:
            pass


def _select_ticket_tier(driver, tier_index: int) -> None:
    """Select a ticket tier by index."""
    try:
        by, selector = SELECTORS["ticket_tier"]
        tiers = driver.find_elements(by, selector)
        if tiers and tier_index < len(tiers):
            tiers[tier_index].click()
            time.sleep(0.5)
    except Exception as e:
        logger.debug(f"Ticket tier selection: {e}")


def _click_buy_button(driver, wait, max_retry: int = 30, interval_ms: int = 100) -> bool:
    """Repeatedly try to click the buy button."""
    for _ in range(max_retry):
        for by, selector in SELECTORS["buy_btn"]:
            try:
                btn = driver.find_element(by, selector)
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    return True
            except NoSuchElementException:
                continue
        time.sleep(interval_ms / 1000)
    return False


def _select_attendees(driver, wait, names: list[str]) -> None:
    """Select attendees by name."""
    try:
        by, selector = SELECTORS["attendee_name"]
        name_elements = driver.find_elements(by, selector)
        checkboxes = driver.find_elements(*SELECTORS["attendee_checkbox"])

        for i, name_el in enumerate(name_elements):
            text = name_el.text
            if any(name in text for name in names):
                if i < len(checkboxes) and not checkboxes[i].is_selected():
                    checkboxes[i].click()
                    time.sleep(0.1)
    except Exception as e:
        logger.debug(f"Attendee selection: {e}")


def _select_attendees_if_needed(driver, names: list[str]) -> bool:
    """Try to select attendees if the attendee page appears."""
    if not names:
        return False
    try:
        by, selector = SELECTORS["attendee_checkbox"]
        checkboxes = driver.find_elements(by, selector)
        if checkboxes:
            _select_attendees(driver, None, names)
            return True
    except Exception:
        pass
    return False


def _click_confirm(driver, wait) -> bool:
    """Click confirm/submit order button."""
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
