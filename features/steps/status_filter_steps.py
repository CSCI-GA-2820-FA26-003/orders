"""Selenium steps for status filtering; REST calls only prepare and clean up fixtures."""

import requests
from behave import given, when, then  # pylint: disable=no-name-in-module
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait


def wait_for_search(context):
    """Wait until the current request finishes and the controls are usable."""
    WebDriverWait(context.driver, context.wait_seconds).until(
        lambda driver: driver.find_element(By.ID, "filter_button").is_enabled()
    )


def remove_fixture(context, order_id):
    """Remove only the order created by this scenario."""
    response = requests.delete(f"{context.base_url}/orders/{order_id}", timeout=context.wait_seconds)
    assert response.status_code == 204, response.text


def create_fixture(context, order_status):
    """Create a known status without depending on existing orders."""
    response = requests.post(
        f"{context.base_url}/orders",
        json={"customer_id": 8501, "status": order_status},
        timeout=context.wait_seconds,
    )
    assert response.status_code == 201, response.text
    order = response.json()
    context.add_cleanup(remove_fixture, context, order["id"])
    return order["id"]


@given("there is a pending order and an order with a different status")
@given('there is a pending order and a "{order_status}" order')
def step_prepare_status_orders(context, order_status="SHIPPED"):
    """Open the page with two orders whose statuses differ."""
    context.pending_order_id = create_fixture(context, "NEW")
    context.other_order_id = create_fixture(context, order_status)
    context.driver.get(context.base_url)
    wait_for_search(context)


@when("I filter the list to pending orders on the admin page")
def step_filter_pending(context):
    """Pending orders use the existing NEW API status."""
    step_filter_status(context, "NEW")


@when('I filter the list to "{order_status}" orders on the admin page')
def step_filter_status(context, order_status):
    """Select a status and submit the real search form."""
    wait_for_search(context)
    Select(context.driver.find_element(By.ID, "filter_status")).select_by_value(order_status)
    context.driver.find_element(By.ID, "filter_button").click()
    wait_for_search(context)


@when("I filter the list to all orders on the admin page")
def step_filter_all(context):
    """An empty selection must omit the status query parameter."""
    step_filter_status(context, "")


@when("I clear the status filter")
def step_clear_status(context):
    """Use the clear action to restore all orders."""
    wait_for_search(context)
    context.driver.find_element(By.ID, "clear_status_filter").click()
    wait_for_search(context)


def result_ids(context):
    """Read IDs from their own cells so partial numeric matches cannot pass."""
    wait_for_search(context)
    return {
        int(cell.text)
        for cell in context.driver.find_elements(By.CSS_SELECTOR, "#order_results td.order-id")
    }


@then("I see the pending order ID in the results")
def step_pending_present(context):
    """The matching NEW order is visible."""
    assert context.pending_order_id in result_ids(context)


@then("the other order ID is absent from the results")
def step_other_absent(context):
    """A different status must be excluded."""
    assert context.other_order_id not in result_ids(context)


@then("I see the other order ID in the results")
def step_other_present(context):
    """The chosen non-NEW status is visible."""
    assert context.other_order_id in result_ids(context)


@then("the pending order ID is absent from the results")
def step_pending_absent(context):
    """The unselected NEW status must be excluded."""
    assert context.pending_order_id not in result_ids(context)


@then("I see both order IDs in the results")
def step_both_present(context):
    """The full list includes both fixture orders again."""
    assert {context.pending_order_id, context.other_order_id} <= result_ids(context)


@then("all statuses are selected")
def step_all_selected(context):
    """Clearing also resets the displayed selection."""
    selected = Select(context.driver.find_element(By.ID, "filter_status")).first_selected_option
    assert selected.get_attribute("value") == ""


def stub_next_search(context, body, response_status):
    """Simulate one list response in the browser, then restore real requests."""
    wait_for_search(context)
    context.driver.execute_script(
        """
        const originalFetch = window.fetch;
        const body = arguments[0];
        const status = arguments[1];
        window.fetch = (url, options) => {
            if (String(url).startsWith(ORDERS_URL) && (!options || options.method === "GET")) {
                window.fetch = originalFetch;
                return Promise.resolve(new Response(JSON.stringify(body), {
                    status, headers: {"Content-Type": "application/json"}
                }));
            }
            return originalFetch(url, options);
        };
        """,
        body,
        response_status,
    )


@given("the next order search returns no matches")
def step_no_matching_orders(context):
    """Exercise an empty result without deleting any existing data."""
    stub_next_search(context, [], 200)


@then("I see that no orders were found")
def step_empty_results(context):
    """The empty response is explained and leaves no stale rows."""
    assert "No orders found" in context.driver.find_element(By.ID, "status_filter_message").text
    assert not result_ids(context)


@given("the next order search fails")
def step_failed_search(context):
    """Simulate the service's normal JSON error envelope."""
    stub_next_search(context, {"status": 503, "error": "Service Unavailable", "message": "Search unavailable"}, 503)


@then("I see an order search error without stale results")
def step_search_error(context):
    """The failure is visible and the old list cannot be mistaken for a result."""
    assert "Search unavailable" in context.driver.find_element(By.ID, "status_filter_message").text
    assert not result_ids(context)
