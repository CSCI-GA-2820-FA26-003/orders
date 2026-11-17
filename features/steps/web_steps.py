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


@given("I have opened an existing order on the admin page")
@given("I have looked up an order on the admin page")
def step_look_up_existing_order(context):
    """Create an order, then show it in the lookup panel"""
    step_create_order(context)
    step_look_up_order(context)
    wait_for_message(context, "alert-success", f"Found order {context.order_id}")


@when("I look up the same order again")
@when("I look up its order ID")
def step_look_up_order(context):
    """Look up the order that the scenario created"""
    look_up(context, context.order_id)


@when("I look up an order ID that does not exist")
def step_look_up_missing_order(context):
    """Look up an ID that no order can have"""
    look_up(context, "0")


@when("I press Look up twice for its order ID")
def step_press_look_up_twice(context):
    """Count the page's lookup requests, then click Look up twice in a row"""
    field = context.driver.find_element(By.ID, "lookup_order_id")
    field.clear()
    field.send_keys(context.order_id)
    context.driver.execute_script(
        """
        window.lookupRequests = 0;
        const realFetch = window.fetch;
        window.fetch = (url, options = {}) => {
            if ((options.method || "GET") === "GET") {
                window.lookupRequests += 1;
            }
            return realFetch(url, options);
        };
        const button = document.getElementById("lookup_button");
        button.click();
        button.click();
        """
    )


@then("only one lookup request was sent")
def step_one_lookup_request(context):
    """Check that the second click did not send another lookup"""
    assert context.driver.execute_script("return window.lookupRequests") == 1
    assert context.driver.find_element(By.ID, "lookup_button").is_enabled()


@then("I see that same ID and the order details I entered")
def step_see_order_details(context):
    """Check the order fields and its item against what was entered"""
    wait_for_message(context, "alert-success", f"Found order {context.order_id}")
    assert detail_text(context, "order_detail_id") == context.order_id
    assert detail_text(context, "order_detail_customer_id") == NEW_ORDER["customer_id"]
    assert detail_text(context, "order_detail_status") == "NEW"
    assert detail_text(context, "order_detail_subtotal") == "25.00"
    cells = context.driver.find_elements(By.CSS_SELECTOR, "#order_detail_items td")
    expected = [NEW_ORDER["product_id"], NEW_ORDER["quantity"], NEW_ORDER["unit_price"], "25.00"]
    assert [cell.text for cell in cells] == expected


@then("I see an order-not-found message")
def step_see_not_found(context):
    """Check that the service's not-found message is shown"""
    wait_for_message(context, "alert-danger", "was not found")


@then("the previous order details are no longer shown")
def step_details_hidden(context):
    """Check that the earlier order is no longer visible"""
    assert not context.driver.find_element(By.ID, "order_details").is_displayed()


def look_up(context, order_id):
    """Enter an order ID in the lookup panel and submit it"""
    field = context.driver.find_element(By.ID, "lookup_order_id")
    field.clear()
    field.send_keys(order_id)
    context.driver.find_element(By.ID, "lookup_button").click()


def detail_text(context, element_id):
    """Return the text of one field in the order details"""
    return context.driver.find_element(By.ID, element_id).text


def wait_for_message(context, css_class, text):
    """Wait for the page to show a message with this style and text"""
    wait = WebDriverWait(context.driver, context.wait_seconds)
    wait.until(expected_conditions.text_to_be_present_in_element((By.ID, "flash_message"), text))
    assert css_class in context.driver.find_element(By.ID, "flash_message").get_attribute("class")


@when("I change an editable detail and save the order")
def step_update_order(context):
    """Change only the customer ID and wait for the update to finish"""
    customer = context.driver.find_element(By.ID, "update_customer_id")
    customer.clear()
    customer.send_keys("1002")
    context.driver.find_element(By.ID, "update_button").click()
    wait_for_message(context, "alert-success", f"Order {context.order_id} updated")


@then("I see the corrected detail under the original order ID")
def step_see_updated_order(context):
    """Check the correction and the unchanged order details after a fresh lookup"""
    wait_for_message(context, "alert-success", f"Found order {context.order_id}")
    assert detail_text(context, "order_detail_id") == context.order_id
    assert detail_text(context, "order_detail_customer_id") == "1002"
    assert detail_text(context, "order_detail_status") == "NEW"
    assert detail_text(context, "order_detail_subtotal") == "25.00"
    cells = context.driver.find_elements(By.CSS_SELECTOR, "#order_detail_items td")
    assert [cell.text for cell in cells] == [
        NEW_ORDER["product_id"], NEW_ORDER["quantity"], NEW_ORDER["unit_price"], "25.00"
    ]


@then("the update form is hidden")
def step_update_form_hidden(context):
    """Check that the previous order cannot be edited after a failed lookup"""
    assert not context.driver.find_element(By.ID, "update_form").is_displayed()


@given("I have created two orders on the admin page")
def step_create_two_orders(context):
    """Create two separate orders through the page and remember their IDs"""
    step_create_order(context)
    context.first_order_id = context.order_id
    step_create_order(context)
    context.second_order_id = context.order_id
    assert context.first_order_id != context.second_order_id


@when("I delete the first order")
def step_delete_first_order(context):
    """Select the first order and delete it through the page"""
    look_up(context, context.first_order_id)
    wait_for_message(context, "alert-success", f"Found order {context.first_order_id}")
    # Typing another ID without looking it up must not change the selected order.
    lookup_field = context.driver.find_element(By.ID, "lookup_order_id")
    lookup_field.clear()
    lookup_field.send_keys(context.second_order_id)
    delete_button = context.driver.find_element(By.ID, "delete_button")
    delete_button.click()
    wait_for_message(context, "alert-success", f"Order {context.first_order_id} deleted")
    step_details_hidden(context)


@then("I cannot find the first order by ID")
def step_first_order_not_found(context):
    """Look up the deleted order and check the service's response"""
    look_up(context, context.first_order_id)
    wait_for_message(context, "alert-danger", f"Order with id [{context.first_order_id}] was not found")


@then("I can still find the second order by ID")
def step_second_order_found(context):
    """Look up the other order and confirm its ID"""
    look_up(context, context.second_order_id)
    wait_for_message(context, "alert-success", f"Found order {context.second_order_id}")
    assert detail_text(context, "order_detail_id") == context.second_order_id
