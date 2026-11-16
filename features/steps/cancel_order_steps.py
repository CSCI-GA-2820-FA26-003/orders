"""Selenium steps for cancellation; REST calls only prepare fulfilled fixtures."""

import requests
from behave import given, when, then  # pylint: disable=no-name-in-module
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


def cancellation_wait(context):
    """Wait for the current lookup or cancellation to release the controls."""
    WebDriverWait(context.driver, context.wait_seconds).until(
        lambda driver: driver.find_element(By.ID, "lookup_button").is_enabled()
    )


def cancellation_notice(context, text, css_class):
    """Check the message and its success or error style."""
    WebDriverWait(context.driver, context.wait_seconds).until(
        lambda driver: text in driver.find_element(By.ID, "flash_message").text
    )
    assert css_class in context.driver.find_element(By.ID, "flash_message").get_attribute("class")


@given("I have opened an order that is eligible for cancellation")
def step_open_cancellable_order(context):
    """Create and look up a NEW order, recording its fields before cancellation."""
    context.execute_steps("Given I have looked up an order on the admin page")
    context.cancel_order_id = context.order_id
    context.cancel_original_details = {
        field: context.driver.find_element(By.ID, f"order_detail_{field}").text
        for field in ("id", "customer_id", "subtotal", "items")
    }
    assert context.driver.find_element(By.ID, "order_detail_status").text == "NEW"
    assert context.driver.find_element(By.ID, "cancel_button").is_enabled()


@when("I cancel it on the admin page")
def step_cancel_opened_order(context):
    """Invoke the real Cancel Order action for the displayed record."""
    context.driver.find_element(By.ID, "cancel_button").click()
    cancellation_wait(context)


@when("I look it up again by the same ID")
def step_reopen_cancelled_order(context):
    """Fetch the record again through the lookup form, using its original ID."""
    cancellation_wait(context)
    field = context.driver.find_element(By.ID, "lookup_order_id")
    field.clear()
    field.send_keys(context.cancel_order_id)
    context.driver.find_element(By.ID, "lookup_button").click()
    cancellation_wait(context)
    cancellation_notice(context, f"Found order {context.cancel_order_id}", "alert-success")


@then("the order is still present and its status shows it was cancelled")
def step_cancelled_record_remains(context):
    """Cancellation retains the original ID, customer, items and subtotal."""
    assert context.driver.find_element(By.ID, "order_details").is_displayed()
    assert context.driver.find_element(By.ID, "order_detail_status").text == "CANCELLED"
    for field, value in context.cancel_original_details.items():
        assert context.driver.find_element(By.ID, f"order_detail_{field}").text == value
    assert not context.driver.find_element(By.ID, "cancel_button").is_enabled()


@when("I enter a different ID without looking it up")
def step_edit_cancellation_lookup(context):
    """An unsubmitted lookup value must not change the selected order."""
    field = context.driver.find_element(By.ID, "lookup_order_id")
    field.clear()
    field.send_keys("0")


@then("I see the cancellation confirmation")
def step_cancellation_confirmation(context):
    """The service's successful cancellation is reported on the page."""
    cancellation_notice(context, f"Order {context.cancel_order_id} cancelled", "alert-success")
    assert context.driver.find_element(By.ID, "order_detail_id").text == context.cancel_order_id
    assert context.driver.find_element(By.ID, "order_detail_status").text == "CANCELLED"


@when("I press Cancel twice before the page responds")
def step_cancel_twice(context):
    """Count cancellation requests and attempt a lookup while cancellation is pending."""
    context.driver.execute_script(
        """
        window.cancelRequests = 0;
        window.lookupsDuringCancel = 0;
        const realFetch = window.fetch;
        window.fetch = (url, options = {}) => {
            if (options.method === "PUT" && String(url).endsWith("/cancel")) {
                window.cancelRequests += 1;
            }
            if ((options.method || "GET") === "GET") {
                window.lookupsDuringCancel += 1;
            }
            return realFetch(url, options);
        };
        const button = document.getElementById("cancel_button");
        button.click();
        window.cancelControlsLocked = button.disabled && document.getElementById("lookup_button").disabled;
        button.click();
        document.getElementById("lookup_form").requestSubmit();
        """
    )
    cancellation_wait(context)


@then("only one cancellation request was sent with lookup locked")
def step_one_cancellation_request(context):
    """Repeated actions cannot issue another cancel or replace the current selection."""
    assert context.driver.execute_script("return window.cancelRequests") == 1
    assert context.driver.execute_script("return window.lookupsDuringCancel") == 0
    assert context.driver.execute_script("return window.cancelControlsLocked")
    assert not context.driver.find_element(By.ID, "cancel_button").is_enabled()


@then("cancellation is disabled and sends no request")
def step_cancellation_disabled(context):
    """Even a programmatic click cannot cancel an absent or ineligible selection."""
    assert not context.driver.find_element(By.ID, "cancel_button").is_enabled()
    requests_sent = context.driver.execute_script(
        """
        let requestsSent = 0;
        const realFetch = window.fetch;
        window.fetch = (...args) => { requestsSent += 1; return realFetch(...args); };
        document.getElementById("cancel_button").dispatchEvent(new Event("click"));
        window.fetch = realFetch;
        return requestsSent;
        """
    )
    assert requests_sent == 0


def set_cancellation_fixture_status(context, order_status):
    """Prepare a fixture with a status that cannot be set through this page."""
    orders_url = context.driver.execute_script("return ORDERS_URL")
    response = requests.put(
        f"{context.base_url}{orders_url}/{context.cancel_order_id}",
        json={"customer_id": int(context.cancel_original_details["customer_id"]), "status": order_status},
        timeout=context.wait_seconds,
    )
    assert response.status_code == 200, response.text


@given('I have opened a "{order_status}" order for cancellation')
def step_open_fulfilled_order(context, order_status):
    """Use the API only to prepare a fulfilled fixture, then look it up on the page."""
    step_open_cancellable_order(context)
    set_cancellation_fixture_status(context, order_status)
    step_reopen_cancelled_order(context)
    assert context.driver.find_element(By.ID, "order_detail_status").text == order_status


@given("the next cancellation request fails")
def step_fail_next_cancellation(context):
    """Simulate one service failure, then restore real requests for the retry."""
    context.driver.execute_script(
        """
        const realFetch = window.fetch;
        window.fetch = (url, options = {}) => {
            if (options.method === "PUT" && String(url).endsWith("/cancel")) {
                window.fetch = realFetch;
                return Promise.resolve(new Response(JSON.stringify({message: "Cancellation unavailable"}), {
                    status: 503, headers: {"Content-Type": "application/json"}
                }));
            }
            return realFetch(url, options);
        };
        """
    )


@then("I see the cancellation error without stale order details")
def step_cancellation_error(context):
    """A failed cancellation cannot be shown as a successful state change."""
    cancellation_notice(context, "Cancellation unavailable", "alert-danger")
    assert not context.driver.find_element(By.ID, "order_details").is_displayed()
    assert not context.driver.find_element(By.ID, "cancel_button").is_enabled()


@then("the order is still eligible for cancellation")
def step_order_still_cancellable(context):
    """The failed request left the same order NEW, and it can be retried."""
    assert context.driver.find_element(By.ID, "order_detail_id").text == context.cancel_order_id
    assert context.driver.find_element(By.ID, "order_detail_status").text == "NEW"
    assert context.driver.find_element(By.ID, "cancel_button").is_enabled()


@given("the displayed order has shipped since it was opened")
def step_fixture_shipped_after_lookup(context):
    """Simulate fulfillment updating the record after the page retrieved it."""
    set_cancellation_fixture_status(context, "SHIPPED")


@then("I see the service's cancellation conflict without stale details")
def step_cancellation_conflict(context):
    """Report the real 409 response, without pretending the order was cancelled."""
    cancellation_notice(context, "has status [SHIPPED] and cannot be cancelled", "alert-danger")
    assert not context.driver.find_element(By.ID, "order_details").is_displayed()
    assert not context.driver.find_element(By.ID, "cancel_button").is_enabled()


@then("the same order is still shipped")
def step_shipped_record_remains(context):
    """The rejected action did not remove or modify the shipped order."""
    assert context.driver.find_element(By.ID, "order_detail_status").text == "SHIPPED"
    for field, value in context.cancel_original_details.items():
        assert context.driver.find_element(By.ID, f"order_detail_{field}").text == value
