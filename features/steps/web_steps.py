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


# The order that the scenarios enter on the page
NEW_ORDER = {
    "customer_id": "1001",
    "product_id": "501",
    "quantity": "2",
    "unit_price": "12.50",
}


@given("I have created an order on the admin page")
def step_create_order(context):
    """Create an order on the page and remember its ID"""
    step_open_admin_page(context)
    step_submit_new_order(context)
    step_see_confirmation_and_id(context)
    context.order_id = context.driver.find_element(By.ID, "created_order_id").text


@when("I fill in the details for a new order")
def step_fill_new_order(context):
    """Fill in the order and its item without submitting the form"""
    for field, value in NEW_ORDER.items():
        element = context.driver.find_element(By.ID, f"create_{field}")
        element.clear()
        element.send_keys(value)


@when("I submit the details for a new order")
def step_submit_new_order(context):
    """Fill in the order and its item, then submit the form"""
    step_fill_new_order(context)
    context.driver.find_element(By.ID, "create_button").click()


@when("I submit a new order without a customer ID")
def step_submit_without_customer(context):
    """Clear the customer ID and submit the form"""
    context.driver.find_element(By.ID, "create_customer_id").clear()
    context.driver.find_element(By.ID, "create_button").click()


@when("I press Create twice before the page responds")
def step_press_create_twice(context):
    """Count the page's create requests, then click Create twice in a row"""
    context.driver.execute_script(
        """
        window.createRequests = 0;
        const realFetch = window.fetch;
        window.fetch = (url, options = {}) => {
            if (options.method === "POST") {
                window.createRequests += 1;
            }
            return realFetch(url, options);
        };
        const button = document.getElementById("create_button");
        button.click();
        button.click();
        """
    )


@then("only one create request was sent")
def step_one_create_request(context):
    """Check that the second click did not send another order"""
    assert context.driver.execute_script("return window.createRequests") == 1
    assert context.driver.find_element(By.ID, "create_button").is_enabled()


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
