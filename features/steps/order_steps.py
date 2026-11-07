"""Browser-only acceptance steps for correcting an existing order."""

# Behave registers these decorators dynamically.
# pylint: disable=not-callable

from behave import given, when, then  # pylint: disable=no-name-in-module
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


def field(context, element_id):
    """Find a page element by its stable ID."""
    return context.driver.find_element(By.ID, element_id)


def fill(context, element_id, value):
    """Replace a form field using browser input."""
    control = field(context, element_id)
    control.clear()
    control.send_keys(str(value))


def wait_message(context, expected):
    """Wait for the outcome and completion of the asynchronous action."""
    WebDriverWait(context.driver, context.wait_seconds).until(
        lambda driver: expected in field(context, "message").text
        and field(context, "create-button").is_enabled()
    )


def snapshot(context):
    """Read persisted details from the selected-order display."""
    return {
        key: field(context, f"selected-{key}").text
        for key in ("id", "customer-id", "status", "subtotal", "created-at", "items")
    }


def lookup(context, order_id):
    """Look up an order through the page and wait for its outcome."""
    fill(context, "lookup-id", order_id)
    field(context, "lookup-button").click()
    WebDriverWait(context.driver, context.wait_seconds).until(
        lambda driver: bool(field(context, "message").text) and field(context, "lookup-button").is_enabled()
    )


@given("I am on the order management page")
def step_management_page(context):
    """Open the page without bypassing the UI for test setup."""
    context.driver.get(context.base_url)


@given("I have opened an existing order on the admin page")
def step_existing_order(context):
    """Create and look up an order with an item that must be preserved."""
    step_management_page(context)
    fill(context, "create-customer-id", 4101)
    for element_id, value in (("product-id", 101), ("quantity", 2), ("unit-price", "12.50")):
        fill(context, f"create-{element_id}", value)
    field(context, "create-button").click()
    wait_message(context, "created.")
    context.original_order = snapshot(context)
    assert context.original_order["id"].isdigit()
    assert context.original_order["customer-id"] == "4101"
    lookup(context, context.original_order["id"])
    wait_message(context, f'Order #{context.original_order["id"]} loaded.')


@when("I change an editable detail and save the order")
def step_save_correction(context):
    """Save a customer correction through the selected order's control."""
    context.corrected_customer = "5101"
    fill(context, "edit-customer-id", context.corrected_customer)
    field(context, "save-button").click()
    wait_message(context, f'Order #{context.original_order["id"]} saved.')


@when("I look up the same order again")
def step_fresh_lookup(context):
    """Reload before lookup so cached details cannot pass the scenario."""
    context.driver.refresh()
    lookup(context, context.original_order["id"])
    wait_message(context, f'Order #{context.original_order["id"]} loaded.')


@then("I see the corrected detail under the original order ID")
def step_verify_correction(context):
    """Verify identity, status, creation time, items and subtotal are preserved."""
    expected = dict(context.original_order, **{"customer-id": context.corrected_customer})
    assert snapshot(context) == expected


@when("I look up an order ID that does not exist")
def step_unknown_order(context):
    """Look up an ID outside the acceptance test database's used range."""
    lookup(context, "2147483647")


@then("I see an order-not-found message and no selected order")
def step_not_found(context):
    """Reject stale details and actions after a failed lookup."""
    wait_message(context, "was not found")
    assert not field(context, "order-details").is_displayed()
    assert not field(context, "save-button").is_enabled()
    assert field(context, "selected-id").get_attribute("textContent") == ""


@when("I create an order with only a product ID")
def step_incomplete_item(context):
    """Leave two item fields blank to exercise form validation."""
    fill(context, "create-customer-id", 4101)
    fill(context, "create-product-id", 101)
    field(context, "create-button").click()


@then("I see an explanation that all item fields are needed")
def step_item_validation(context):
    """Verify the failed operation leaves no phantom selected order."""
    wait_message(context, "Fill all three item fields")
    assert field(context, "message").get_attribute("data-error") == "true"
    assert not field(context, "order-details").is_displayed()
