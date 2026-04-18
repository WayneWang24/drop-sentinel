"""Multi-device Appium controller."""
from __future__ import annotations

import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from appium import webdriver
from appium.options.android import UiAutomator2Options

from drop_sentinel.auto.config import AutoConfig, DeviceConfig

logger = logging.getLogger(__name__)


class DeviceSession:
    """Manages a single Appium session for one device."""

    def __init__(self, device: DeviceConfig, driver: webdriver.Remote):
        self.device = device
        self.driver = driver

    def screenshot(self, path: str) -> None:
        """Save a screenshot."""
        self.driver.save_screenshot(path)

    def quit(self) -> None:
        """Close the Appium session."""
        try:
            self.driver.quit()
        except Exception:
            pass


class MultiDeviceController:
    """Controls multiple Android devices/emulators via Appium."""

    def __init__(self, config: AutoConfig):
        self.config = config
        self.sessions: list[DeviceSession] = []

    def discover_devices(self) -> list[str]:
        """List connected ADB devices."""
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True, text=True, timeout=10,
            )
            lines = result.stdout.strip().split("\n")[1:]  # Skip header
            devices = []
            for line in lines:
                parts = line.strip().split("\t")
                if len(parts) == 2 and parts[1] == "device":
                    devices.append(parts[0])
            return devices
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Failed to discover devices: {e}")
            return []

    def connect(self, device: DeviceConfig, app_package: str, app_activity: str) -> DeviceSession | None:
        """Create an Appium session for a single device."""
        options = UiAutomator2Options()
        options.platform_name = "Android"
        options.platform_version = device.platform_version
        options.udid = device.udid
        options.system_port = device.system_port
        options.no_reset = True  # Keep app state (login session)
        options.auto_grant_permissions = True
        options.app_package = app_package
        options.app_activity = app_activity
        options.new_command_timeout = 300

        appium_url = f"http://127.0.0.1:{device.appium_port}"

        try:
            driver = webdriver.Remote(appium_url, options=options)
            session = DeviceSession(device, driver)
            self.sessions.append(session)
            logger.info(f"Connected to {device.name} ({device.udid})")
            return session
        except Exception as e:
            logger.error(f"Failed to connect to {device.name}: {e}")
            return None

    def connect_all(self, app_package: str, app_activity: str) -> list[DeviceSession]:
        """Connect to all configured devices."""
        sessions = []
        for device in self.config.devices:
            session = self.connect(device, app_package, app_activity)
            if session:
                sessions.append(session)
        return sessions

    def run_parallel(
        self,
        task: Callable[[DeviceSession], dict],
        sessions: list[DeviceSession] | None = None,
    ) -> list[dict]:
        """Run a task on all sessions in parallel.

        Args:
            task: Function that takes a DeviceSession and returns a result dict.
            sessions: Sessions to use. Defaults to all active sessions.

        Returns:
            List of result dicts from each session.
        """
        target_sessions = sessions or self.sessions
        if not target_sessions:
            logger.warning("No active sessions")
            return []

        results = []
        with ThreadPoolExecutor(max_workers=len(target_sessions)) as executor:
            futures = {
                executor.submit(task, session): session
                for session in target_sessions
            }
            for future in as_completed(futures):
                session = futures[future]
                try:
                    result = future.result()
                    result["device"] = session.device.name
                    results.append(result)
                except Exception as e:
                    logger.error(f"Task failed on {session.device.name}: {e}")
                    results.append({
                        "device": session.device.name,
                        "success": False,
                        "error": str(e),
                    })
                    if self.config.screenshot_on_error:
                        self._save_error_screenshot(session)

        return results

    def synchronized_start(
        self,
        task: Callable[[DeviceSession], dict],
        start_time: float,
        sessions: list[DeviceSession] | None = None,
    ) -> list[dict]:
        """Wait until start_time, then run task on all devices simultaneously.

        Args:
            task: Function to execute on each device.
            start_time: Unix timestamp to start execution.
            sessions: Sessions to use.
        """
        now = time.time()
        wait = start_time - now
        if wait > 0:
            logger.info(f"Waiting {wait:.1f}s until start time...")
            # Sleep until 0.5s before target
            if wait > 0.5:
                time.sleep(wait - 0.5)
            # Busy-wait for precision
            while time.time() < start_time:
                pass

        logger.info("GO! Starting parallel execution")
        return self.run_parallel(task, sessions)

    def disconnect_all(self) -> None:
        """Close all Appium sessions."""
        for session in self.sessions:
            session.quit()
        self.sessions.clear()
        logger.info("All sessions disconnected")

    def _save_error_screenshot(self, session: DeviceSession) -> None:
        """Save an error screenshot."""
        try:
            path = Path(self.config.screenshot_dir)
            path.mkdir(parents=True, exist_ok=True)
            filename = f"{session.device.name}_{int(time.time())}.png"
            session.screenshot(str(path / filename))
        except Exception:
            pass
