"""Selenium steps for cancellation; REST calls only prepare fulfilled fixtures."""

import requests
from behave import given, when, then  # pylint: disable=no-name-in-module
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait


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


@when('I start "{action}" and try the other order actions')
def step_try_competing_order_actions(context, action):
    """Hold the first request until save, cancel and lookup have all been attempted."""
    assert action in {"save", "cancel", "delete"}
    context.driver.execute_script(
        """
        const action = arguments[0];
        const realFetch = window.fetch;
        window.orderActionRequests = [];
        window.fetch = (url, options = {}) => {
            window.orderActionRequests.push({url: String(url), method: options.method || "GET"});
            return new Promise(resolve => {
                window.releaseOrderAction = () => {
                    window.fetch = realFetch;
                    resolve(realFetch(url, options));
                };
            });
        };
        document.getElementById("update_customer_id").value = "1002";
        if (action === "save") {
            document.getElementById("update_form").requestSubmit();
        } else if (action === "cancel") {
            document.getElementById("cancel_button").click();
        } else {
            document.getElementById("delete_button").click();
        }
        window.orderActionControlsLocked = ["lookup_button", "update_button", "cancel_button", "delete_button"]
            .every(id => document.getElementById(id).disabled);
        document.getElementById("update_form").requestSubmit();
        document.getElementById("cancel_button").dispatchEvent(new Event("click"));
        document.getElementById("delete_button").dispatchEvent(new Event("click"));
        document.getElementById("lookup_form").requestSubmit();
        """,
        action,
    )


@then('only the "{action}" request is sent while all order controls are locked')
def step_only_one_order_action(context, action):
    """Check the lock before releasing a real request to the service."""
    calls = context.driver.execute_script("return window.orderActionRequests")
    assert len(calls) == 1, calls
    suffix = f"/{context.cancel_order_id}" + ("/cancel" if action == "cancel" else "")
    assert calls[0]["url"].endswith(suffix), calls
    assert calls[0]["method"] == ("DELETE" if action == "delete" else "PUT")
    assert context.driver.execute_script("return window.orderActionControlsLocked")
    context.driver.execute_script("window.releaseOrderAction()")
    cancellation_wait(context)
    outcome = {"save": "updated", "cancel": "cancelled", "delete": "deleted"}[action]
    cancellation_notice(context, f"Order {context.cancel_order_id} {outcome}", "alert-success")


@then('the "{action}" result remains after looking up the same order')
def step_order_action_persists(context, action):
    """Verify the saved change or cancellation was not overwritten by a competing action."""
    if action == "delete":
        field = context.driver.find_element(By.ID, "lookup_order_id")
        field.clear()
        field.send_keys(context.cancel_order_id)
        context.driver.find_element(By.ID, "lookup_button").click()
        cancellation_wait(context)
        cancellation_notice(context, f"Order with id [{context.cancel_order_id}] was not found", "alert-danger")
        assert not context.driver.find_element(By.ID, "order_details").is_displayed()
        for button in ("update_button", "cancel_button", "delete_button"):
            assert not context.driver.find_element(By.ID, button).is_enabled()
        return
    step_reopen_cancelled_order(context)
    expected_status = "NEW" if action == "save" else "CANCELLED"
    assert context.driver.find_element(By.ID, "order_detail_status").text == expected_status
    expected_customer = "1002" if action == "save" else context.cancel_original_details["customer_id"]
    assert context.driver.find_element(By.ID, "order_detail_customer_id").text == expected_customer
    assert context.driver.find_element(By.ID, "update_status").get_attribute("value") == expected_status
    assert context.driver.find_element(By.ID, "cancel_button").is_enabled() == (action == "save")


@when('I save the displayed order with status "{order_status}"')
def step_save_order_status(context, order_status):
    """Saving fulfillment must also refresh the order's cancellation eligibility."""
    Select(context.driver.find_element(By.ID, "update_status")).select_by_value(order_status)
    step_save_displayed_order(context)
    cancellation_notice(context, f"Order {context.cancel_order_id} updated", "alert-success")


@given("the next save request fails")
def step_fail_next_save(context):
    """Simulate one save failure without changing the real order."""
    context.driver.execute_script(
        """
        const realFetch = window.fetch;
        window.fetch = (url, options = {}) => {
            if (options.method === "PUT" && !String(url).endsWith("/cancel")) {
                window.fetch = realFetch;
                return Promise.resolve(new Response(JSON.stringify({message: "Update unavailable"}), {
                    status: 503, headers: {"Content-Type": "application/json"}
                }));
            }
            return realFetch(url, options);
        };
        """
    )


@when("I save the displayed order")
def step_save_displayed_order(context):
    """Save the form for the displayed order, then wait for its controls to unlock."""
    context.driver.find_element(By.ID, "update_button").click()
    cancellation_wait(context)


@then("I see the save error without stale order details")
def step_save_error_clears_selection(context):
    """A failed save clears both selections and blocks a hidden form resubmission."""
    cancellation_notice(context, "Update unavailable", "alert-danger")
    assert not context.driver.find_element(By.ID, "order_details").is_displayed()
    assert not context.driver.find_element(By.ID, "update_button").is_enabled()
    assert not context.driver.find_element(By.ID, "delete_button").is_enabled()
    requests_sent = context.driver.execute_script(
        """
        let requestsSent = 0;
        const realFetch = window.fetch;
        window.fetch = (...args) => { requestsSent += 1; return realFetch(...args); };
        document.getElementById("update_form").requestSubmit();
        document.getElementById("delete_button").dispatchEvent(new Event("click"));
        window.fetch = realFetch;
        return requestsSent;
        """
    )
    assert requests_sent == 0


@then("the full list contains the cancelled order")
def step_list_contains_cancelled_order(context):
    """The recently merged list UI must include the cancellation's persisted status."""
    cancellation_notice(context, "Orders loaded", "alert-success")
    rows = context.driver.find_elements(By.CSS_SELECTOR, "#list_rows tr")
    visible = [tuple(cell.text for cell in row.find_elements(By.TAG_NAME, "td")) for row in rows]
    assert (context.cancel_order_id, "CANCELLED") in visible
