"""Pop Mart WeChat mini-program automated lottery/purchase."""
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

from drop_sentinel.auto.config import PopMartTarget
from drop_sentinel.auto.controller import DeviceSession

logger = logging.getLogger(__name__)

# WeChat identifiers
WECHAT_PACKAGE = "com.tencent.mm"
WECHAT_ACTIVITY = "com.tencent.mm.ui.LauncherUI"

# Pop Mart mini-program selectors (WeChat WebView context)
SELECTORS = {
    # 微信搜索
    "wechat_search": (AppiumBy.XPATH, '//*[contains(@content-desc,"搜索")]'),
    "search_input": (AppiumBy.XPATH, '//android.widget.EditText'),
    # 小程序入口
    "mini_program_tab": (AppiumBy.XPATH, '//*[contains(@text,"小程序")]'),
    "popmart_mini": (AppiumBy.XPATH, '//*[contains(@text,"泡泡玛特")]'),
    # 抽签相关
    "lottery_tab": [
        (AppiumBy.XPATH, '//*[contains(@text,"抽签")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"抽签购")]'),
    ],
    "lottery_signup": [
        (AppiumBy.XPATH, '//*[contains(@text,"立即报名")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"我要报名")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"参与抽签")]'),
    ],
    "lottery_confirm": [
        (AppiumBy.XPATH, '//*[contains(@text,"确认报名")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"确认")]'),
    ],
    # 购买相关
    "buy_btn": [
        (AppiumBy.XPATH, '//*[contains(@text,"立即购买")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"立即抢购")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"加入购物车")]'),
    ],
    "confirm_order": [
        (AppiumBy.XPATH, '//*[contains(@text,"提交订单")]'),
        (AppiumBy.XPATH, '//*[contains(@text,"确认订单")]'),
    ],
    # 产品搜索
    "product_search": (AppiumBy.XPATH, '//android.widget.EditText[contains(@hint,"搜索")]'),
}


def signup_lottery(session: DeviceSession, target: PopMartTarget) -> dict:
    """Sign up for a Pop Mart lottery (抽签报名).

    Prerequisites:
        - WeChat is open and logged in
        - Pop Mart mini-program has been used before (in recent list)

    Returns:
        dict with keys: success, message
    """
    driver = session.driver
    wait = WebDriverWait(driver, 15)
    result = {"success": False, "message": ""}

    try:
        # Step 1: Open Pop Mart mini-program
        _open_popmart_mini(driver, wait)

        # Step 2: Navigate to lottery section
        _navigate_to_lottery(driver, wait)

        # Step 3: Find target product
        if target.product_name:
            _find_product(driver, target.product_name)

        # Step 4: Click signup
        signed = _click_lottery_signup(driver, wait)
        if signed:
            # Step 5: Confirm
            confirmed = _click_lottery_confirm(driver, wait)
            if confirmed:
                result["success"] = True
                result["message"] = f"抽签报名成功: {target.product_name}"
            else:
                result["message"] = "确认报名失败"
        else:
            result["message"] = "未找到报名按钮（可能未到报名时间或已报名）"

    except TimeoutException:
        result["message"] = "操作超时"
    except Exception as e:
        result["message"] = f"异常: {e}"
        logger.error(f"Lottery signup error on {session.device.name}: {e}")

    return result


def flash_purchase(session: DeviceSession, target: PopMartTarget) -> dict:
    """Attempt flash sale purchase on Pop Mart mini-program.

    For products that use timed flash sale (定时抢购) instead of lottery.

    Prerequisites:
        - WeChat is open and logged in
        - Already on the product page in Pop Mart mini-program
    """
    driver = session.driver
    result = {"success": False, "message": ""}

    # Rapid-fire buy attempts
    for attempt in range(100):
        try:
            for by, selector in SELECTORS["buy_btn"]:
                try:
                    btn = driver.find_element(by, selector)
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        logger.info(f"{session.device.name}: Buy clicked (attempt {attempt+1})")
                        time.sleep(0.3)

                        # Try to confirm order
                        if _click_order_confirm(driver):
                            result["success"] = True
                            result["message"] = f"订单已提交 (attempt {attempt+1})"
                            return result
                except NoSuchElementException:
                    continue

            time.sleep(0.1)
        except Exception as e:
            logger.debug(f"Attempt {attempt+1}: {e}")

    result["message"] = "所有尝试均失败"
    return result


def _open_popmart_mini(driver, wait) -> None:
    """Open Pop Mart mini-program from WeChat."""
    # Try recent mini-programs first (pull down on chat list)
    try:
        # Swipe down to show recent mini-programs
        size = driver.get_window_size()
        start_x = size["width"] // 2
        driver.swipe(start_x, 300, start_x, 800, duration=300)
        time.sleep(1)

        # Look for Pop Mart
        by, selector = SELECTORS["popmart_mini"]
        el = driver.find_element(by, selector)
        el.click()
        time.sleep(3)  # Wait for mini-program to load
        return
    except NoSuchElementException:
        pass

    # Fall back to search
    try:
        by, selector = SELECTORS["wechat_search"]
        driver.find_element(by, selector).click()
        time.sleep(0.5)

        by, selector = SELECTORS["search_input"]
        search = wait.until(EC.presence_of_element_located((by, selector)))
        search.send_keys("泡泡玛特")
        time.sleep(1)

        by, selector = SELECTORS["mini_program_tab"]
        driver.find_element(by, selector).click()
        time.sleep(1)

        by, selector = SELECTORS["popmart_mini"]
        driver.find_element(by, selector).click()
        time.sleep(3)
    except Exception as e:
        logger.warning(f"Failed to open Pop Mart mini-program: {e}")
        raise


def _navigate_to_lottery(driver, wait) -> None:
    """Navigate to the lottery/抽签 section."""
    for by, selector in SELECTORS["lottery_tab"]:
        try:
            el = driver.find_element(by, selector)
            el.click()
            time.sleep(2)
            return
        except NoSuchElementException:
            continue
    logger.warning("Lottery tab not found")


def _find_product(driver, product_name: str) -> None:
    """Search for a specific product."""
    try:
        by, selector = SELECTORS["product_search"]
        search = driver.find_element(by, selector)
        search.click()
        search.send_keys(product_name)
        time.sleep(2)

        # Click first matching result
        results = driver.find_elements(
            AppiumBy.XPATH,
            f'//android.widget.TextView[contains(@text,"{product_name[:6]}")]',
        )
        if results:
            results[0].click()
            time.sleep(1)
    except Exception as e:
        logger.debug(f"Product search: {e}")


def _click_lottery_signup(driver, wait) -> bool:
    """Click the lottery signup button."""
    for by, selector in SELECTORS["lottery_signup"]:
        try:
            btn = driver.find_element(by, selector)
            if btn.is_displayed():
                btn.click()
                return True
        except NoSuchElementException:
            continue
    return False


def _click_lottery_confirm(driver, wait) -> bool:
    """Click the lottery confirmation button."""
    time.sleep(0.5)
    for by, selector in SELECTORS["lottery_confirm"]:
        try:
            btn = wait.until(EC.element_to_be_clickable((by, selector)))
            btn.click()
            return True
        except (NoSuchElementException, TimeoutException):
            continue
    return False


def _click_order_confirm(driver) -> bool:
    """Try to click order confirmation."""
    for by, selector in SELECTORS["confirm_order"]:
        try:
            btn = driver.find_element(by, selector)
            if btn.is_displayed():
                btn.click()
                return True
        except NoSuchElementException:
            continue
    return False
