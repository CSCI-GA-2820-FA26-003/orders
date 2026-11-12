"""
Steps that use the Orders admin page through Selenium
"""

from behave import given, when, then  # pylint: disable=no-name-in-module
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait


@given("I am on the Orders admin page")
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


@when("I submit the details for a new order")
def step_submit_new_order(context):
    """Fill in the order and its item, then submit the form"""
    context.driver.find_element(By.ID, "create_customer_id").send_keys("1001")
    context.driver.find_element(By.ID, "create_product_id").send_keys("501")
    context.driver.find_element(By.ID, "create_quantity").send_keys("2")
    context.driver.find_element(By.ID, "create_unit_price").send_keys("12.50")
    context.driver.find_element(By.ID, "create_button").click()


@when("I submit a new order without a customer ID")
def step_submit_without_customer(context):
    """Submit the form with the customer ID left blank"""
    context.driver.find_element(By.ID, "create_button").click()


@then("I see a creation confirmation and the new order ID")
def step_see_confirmation_and_id(context):
    """Check the confirmation message and the assigned order ID"""
    wait_for_message(context, "alert-success", "Order created")
    order_id = context.driver.find_element(By.ID, "created_order_id")
    assert order_id.is_displayed()
    assert order_id.text.isdigit()


@then("I see a message explaining what is wrong")
def step_see_error_message(context):
    """Check that the service's validation error names the missing field"""
    wait_for_message(context, "alert-danger", "customer_id")


@then("no order ID is shown")
def step_no_order_id(context):
    """Check that no new order ID is visible"""
    assert not context.driver.find_element(By.ID, "created_order").is_displayed()


def wait_for_message(context, css_class, text):
    """Wait for the page to show a message with this style and text"""
    wait = WebDriverWait(context.driver, context.wait_seconds)
    wait.until(expected_conditions.text_to_be_present_in_element((By.ID, "flash_message"), text))
    assert css_class in context.driver.find_element(By.ID, "flash_message").get_attribute("class")
