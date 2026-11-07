"""
Environment for Behave testing
"""

from os import getenv
from selenium import webdriver

BASE_URL = getenv("BASE_URL", "http://localhost:8080")
WAIT_SECONDS = int(getenv("WAIT_SECONDS", "30"))


def before_all(context):
    """Start a headless browser before the tests run"""
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless")
    context.base_url = BASE_URL
    context.wait_seconds = WAIT_SECONDS
    context.driver = webdriver.Chrome(options=options)
    context.driver.implicitly_wait(context.wait_seconds)
    context.driver.set_window_size(1280, 1300)
    context.config.setup_logging()


def after_all(context):
    """Close the browser after the tests run"""
    context.driver.quit()
