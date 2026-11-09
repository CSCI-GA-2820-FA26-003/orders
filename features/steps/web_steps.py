"""
Steps that use the Orders admin page through Selenium
"""

# Behave registers these decorators dynamically.
# pylint: disable=not-callable

from behave import when, then  # pylint: disable=no-name-in-module
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait


@when("I open the Orders admin page")
def step_open_admin_page(context):
    """Load the admin page in the browser"""
    context.driver.get(context.base_url)


@then("I see the Orders heading")
def step_see_orders_heading(context):
    """Wait for the page heading to show Orders"""
    found = WebDriverWait(context.driver, context.wait_seconds).until(
        expected_conditions.text_to_be_present_in_element((By.TAG_NAME, "h1"), "Orders")
    )
    assert found
